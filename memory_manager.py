# memory_manager.py
import uuid
from datetime import datetime
from db import SessionLocal, MemoryRow
from retriever import top_k_similar, _get_rows
from llm_client import call_model
from config import TOKEN_BUDGET
import math

class MemoryManager:
    def __init__(self, token_budget=TOKEN_BUDGET):
        self.token_budget = token_budget
        self._context_cache = {}  # LRU query cache

    def add_memory(self, text, parent_id=None, conversation_id=None, pinned=False, is_assistant=False):
        row = MemoryRow(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            text=text,
            parent_id=parent_id,
            pinned=pinned,
            timestamp=datetime.utcnow(),
            is_longterm=False,
            is_assistant=is_assistant
        )
        db = SessionLocal()
        db.add(row)
        db.commit()
        db.refresh(row)
        
        # Clear cache since new memory was added
        self._context_cache.clear()
        
        # Proactive Summarization: if STM > 6 unpinned msgs, trigger distillation
        stm_count = db.query(MemoryRow).filter(MemoryRow.is_longterm==False, MemoryRow.pinned==False).count()
        db.close()
        
        if stm_count > 6:
            self.ensure_within_budget(force_summarize=True)
            
        return {"id": row.id}

    def _all_rows(self):
        db = SessionLocal()
        rows = db.query(MemoryRow).all()
        db.close()
        return rows

    def total_token_estimate(self):
        # crude token estimate: 0.75 tokens per word
        db = SessionLocal()
        rows = db.query(MemoryRow).all()
        total = 0
        for r in rows:
            w = len((r.summary or r.text).split())
            total += int(w * 0.75)
        db.close()
        return total

    def ensure_within_budget(self, force_summarize=False):
        # compress low-importance non-pinned items until within budget (or if proactively forced)
        db = SessionLocal()
        while self.total_token_estimate() > self.token_budget or force_summarize:
            # pick low importance, non-pinned, non-longterm
            candidate = db.query(MemoryRow).filter(MemoryRow.pinned==False, MemoryRow.is_longterm==False).order_by(MemoryRow.importance.asc(), MemoryRow.timestamp.asc()).first()
            if not candidate:
                break
            # pick up to 2 more low ones
            others = db.query(MemoryRow).filter(MemoryRow.id != candidate.id, MemoryRow.pinned==False, MemoryRow.is_longterm==False).order_by(MemoryRow.importance.asc(), MemoryRow.timestamp.asc()).limit(2).all()
            to_combine = [candidate] + others
            combined_text = " ".join([t.text for t in to_combine])
            # ask remote LLM to summarize (safer than local HF on mac)
            prompt = "Summarize the following conversation excerpts into a concise, accurate summary (1-2 short paragraphs). Do NOT add new facts.\n\n" + combined_text
            try:
                summary = call_model(prompt, max_tokens=300)
            except Exception:
                # fallback: naive truncate
                summary = combined_text[:400] + "..."
            # create new longterm row with summary text
            new_row = MemoryRow(
                id=str(uuid.uuid4()),
                conversation_id=None,
                text=combined_text,
                summary=summary,
                parent_id=None,
                pinned=False,
                importance=900,
                timestamp=datetime.utcnow(),
                is_longterm=True
            )
            # delete old ones and add new summary
            for t in to_combine:
                db.delete(t)
            db.add(new_row)
            db.commit()
            force_summarize = False # turn off after one batch if forced
        db.close()

    def compute_importance_scores(self, query=None, conversation_id=None):
        # compute importance = 0.6*similarity + 0.3*recency + 0.1*pinned
        rows = _get_rows(conversation_id)
        now = datetime.utcnow()
        # get similarity scores from retriever
        sims_map = {}
        if query:
            sims = top_k_similar(query, conversation_id=conversation_id, k=len(rows))
            for r, score in sims:
                sims_map[r.id] = score
        db = SessionLocal()
        for r in rows:
            sim = sims_map.get(r.id, 0.0)
            recency = 1.0 / (1.0 + (now - r.timestamp).total_seconds()/60.0)
            pinned_val = 0.2 if r.pinned else 0.0
            score = 0.6*sim + 0.3*recency + pinned_val
            r.importance = int(score * 1000)
            db.merge(r)
        db.commit()
        db.close()

    def get_stats(self):
        """Returns statistics about the hierarchical memory system."""
        db = SessionLocal()
        stm_count = db.query(MemoryRow).filter(MemoryRow.is_longterm == False, MemoryRow.pinned == False).count()
        ltm_count = db.query(MemoryRow).filter(MemoryRow.is_longterm == True).count()
        pinned_count = db.query(MemoryRow).filter(MemoryRow.pinned == True).count()
        total_tokens = self.total_token_estimate()
        db.close()
        return {
            "stm": stm_count,
            "ltm": ltm_count,
            "pinned": pinned_count,
            "total_tokens": total_tokens,
            "budget": self.token_budget
        }

    def retrieve_context_for_prompt(self, user_query, conversation_id=None, top_k=6):
        cache_key = f"{user_query}_{conversation_id}_{top_k}"
        if cache_key in self._context_cache:
            return self._context_cache[cache_key]

        # 1. Update importance relative to current query
        self.compute_importance_scores(user_query, conversation_id=conversation_id)
        
        db = SessionLocal()
        # 2. Fetch top candidates based on combined score
        rows = db.query(MemoryRow).filter(
            (MemoryRow.conversation_id == conversation_id) | (MemoryRow.conversation_id == None)
        ).order_by(MemoryRow.importance.desc()).limit(top_k).all()
        
        contexts = []
        seen = set()
        
        for r in rows:
            if r.id in seen: continue
            
            # 3. Contextual Enrichment: Include parents or related snippets
            content = r.summary or r.text
            
            # If it's a summarized LTM, mention it's a "Memory Consolidation"
            if r.is_longterm:
                content = f"[PAST INSIGHT]: {content}"
            elif r.pinned:
                content = f"[USER PINNED]: {content}"
                
            contexts.append(content)
            seen.add(r.id)
            
            # 4. Grab parent if conversational thread
            if r.parent_id:
                parent = db.query(MemoryRow).filter(MemoryRow.id == r.parent_id).first()
                if parent and parent.id not in seen:
                    contexts.append(parent.summary or parent.text)
                    seen.add(parent.id)
        
        db.close()
        self._context_cache[cache_key] = contexts
        return contexts
                    
    def get_memories(self, category="stm", conversation_id=None):
        """Fetches raw memory content for UI inspection."""
        db = SessionLocal()
        if category == "stm":
            rows = db.query(MemoryRow).filter(MemoryRow.is_longterm == False, MemoryRow.pinned == False).order_by(MemoryRow.timestamp.desc()).all()
        elif category == "ltm":
            rows = db.query(MemoryRow).filter(MemoryRow.is_longterm == True).order_by(MemoryRow.timestamp.desc()).all()
        elif category == "pinned":
            rows = db.query(MemoryRow).filter(MemoryRow.pinned == True).order_by(MemoryRow.timestamp.desc()).all()
        else:
            rows = []
        
        result = [{"text": r.summary or r.text, "timestamp": str(r.timestamp), "id": r.id} for r in rows]
        db.close()
        return result
