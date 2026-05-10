# app.py
import os
# macOS safety flags (must be set BEFORE any heavy imports)
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI

app = FastAPI(title="LLM Memory Backend (safe-mac)")
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],  # frontend URLs
    allow_credentials=True,
    allow_methods=["*"],  # important for OPTIONS
    allow_headers=["*"],  # important for custom headers like JSON
)



# optional: ensure spawn for multiprocessing (macOS friendly)
import multiprocessing
try:
    multiprocessing.set_start_method("spawn", force=True)
except RuntimeError:
    # if already set, ignore
    pass

import re
import psutil
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from memory_manager import MemoryManager
from prompt_builder import PromptBuilder
from llm_client import call_model
from fact_store import detect_and_save_fact, search_facts

app = FastAPI(title="LLM Memory Backend (safe-mac)")

from security_preprocessor import SecurityPreprocessor
from security_manager import SecurityManager
from swarm_orchestrator import SwarmOrchestrator

# single, shared instance
sm = SecurityManager()
mm = MemoryManager()
pb = PromptBuilder(mm)
sp = SecurityPreprocessor()
so = SwarmOrchestrator()

class ChatMessage(BaseModel):
    conversation_id: str | None = None
    parent_id: str | None = None
    message: str
    pinned: bool = False
    mode: str = "Modern"
    sentient: bool = False
    custom_agent: str | None = None

@app.get("/")
def root():
    return {"status": "ok", "note": "Run POST /chat to interact"}

@app.get("/stats")
def stats():
    return mm.get_stats()

@app.get("/hardware_metrics")
def hardware_metrics():
    # Cognitive Load mapped to physical Mac CPU Core Utilization
    load = int(psutil.cpu_percent(interval=0.1))
    # Neural Sync mapped to physical Mac RAM Availability (100% - usage)
    mem = psutil.virtual_memory()
    sync = round(100.0 - mem.percent, 1)
    return {"load": load, "sync": sync}

@app.get("/memories")
def get_memories(category: str = "stm"):
    return mm.get_memories(category=category)

from tools import TOOL_MAP

@app.get("/facts")
def get_all_facts_endpoint():
    from fact_store import get_all_facts
    return get_all_facts()


@app.post("/chat")
def chat(req: ChatMessage):
    query_lower = req.message.lower().strip()

    # ── FACT TEACHING: Detect if user is providing a new fact ────────────────
    # e.g. "the MLA of Chepauk is Udhayanidhi Stalin"
    learned = detect_and_save_fact(req.message)
    if learned:
        confirm = (
            f"Got it! I've saved that to my database: "
            f"The {learned['predicate']} of {learned['subject']} is {learned['value']}. "
            f"I'll remember this for future queries."
        )
        user_mem = mm.add_memory(req.message, parent_id=req.parent_id, conversation_id=req.conversation_id, pinned=req.pinned)
        mm.add_memory(confirm, parent_id=user_mem["id"], conversation_id=req.conversation_id, is_assistant=True)
        return {
            "assistant": confirm,
            "thought": f"User taught me a new fact: {learned}",
            "actions": [{"tool": "save_fact", "result": learned}],
            "security": {"risk_level": "Low", "reason": "Fact-learning path."},
            "user_memory_id": user_mem["id"]
        }

    # ── FACT QUERY: Check fact DB before hitting RAG ─────────────────────────
    # Only treat the message as a fact query if it looks like a question.
    question_words = {"who", "what", "which", "where", "when", "how", "why", "whose", "whom"}
    first_word = query_lower.split()[0] if query_lower.split() else ""
    is_question = query_lower.endswith("?") or first_word in question_words

    raw_fact_hits = search_facts(req.message, top_k=5) if is_question else []

    # Filter facts so that the subject actually overlaps with the query terms.
    # This prevents answering with unrelated entries (e.g., returning Karnataka
    # when the user asked about Tamil Nadu).
    def _tokenize(text: str) -> set[str]:
        return {t for t in re.split(r"[^a-zA-Z0-9]+", text.lower()) if t}

    query_tokens = _tokenize(req.message)
    fact_hits = []
    for f in raw_fact_hits:
        subject_tokens = _tokenize(f.get("subject", ""))
        # Require at least one shared token between query and subject.
        if subject_tokens and (subject_tokens & query_tokens):
            fact_hits.append(f)

    if fact_hits:
        # Build a direct answer from saved facts (including conflicts).
        # If multiple values exist for the same (subject,predicate), we cite the
        # oldest as the DB baseline, and mention the other taught values as
        # "also".
        fact_groups: dict[tuple[str, str], list[dict]] = {}
        for f in fact_hits:
            key = (f["subject"], f["predicate"])
            fact_groups.setdefault(key, []).append(f)

        fact_lines: list[str] = []
        for (subject, predicate), group in fact_groups.items():
            # ISO8601 timestamps sort lexicographically in UTC.
            ordered = sorted(group, key=lambda x: x.get("created_at", ""))
            canonical = ordered[0]["value"] if ordered else ""
            others = [x["value"] for x in ordered[1:]]
            # Keep order but avoid repeating the same value.
            uniq_others = []
            for v in others:
                if v not in uniq_others:
                    uniq_others.append(v)

            if uniq_others:
                also = ", ".join(uniq_others)
                fact_lines.append(
                    f"According to my database, the {predicate} of {subject} is {canonical}, but I also have it as {also}."
                )
            else:
                fact_lines.append(f"The {predicate} of {subject} is {canonical}.")

        fact_reply = "Based on information stored in my database:\n- " + "\n- ".join(fact_lines)
        user_mem = mm.add_memory(req.message, parent_id=req.parent_id, conversation_id=req.conversation_id, pinned=req.pinned)
        mm.add_memory(fact_reply, parent_id=user_mem["id"], conversation_id=req.conversation_id, is_assistant=True)
        return {
            "assistant": fact_reply,
            "thought": f"Retrieved {len(fact_hits)} fact(s) from the fact database.",
            "actions": [{"tool": "search_facts", "result": fact_hits}],
            "security": {"risk_level": "Low", "reason": "Fact-retrieval path."},
            "user_memory_id": user_mem["id"]
        }

    # -1. Fast-Path Intent Router (Bypass RAG/Tooling for speed)
    fast_intents = ["hi", "hello", "hey", "who are you", "what are you", "help", "how are you"]
    if len(query_lower) < 25 and any(i in query_lower for i in fast_intents):
        # Skip heavy Security/FAISS PyTorch embeddings entirely!
        fast_reply = call_model(f"You are Synthaura Prime, a highly advanced 2026 AI. Answer this simple greeting instantly and concisely: {req.message}")
        user_mem = mm.add_memory(req.message, parent_id=req.parent_id, conversation_id=req.conversation_id, pinned=req.pinned)
        mm.add_memory(fast_reply, parent_id=user_mem["id"], conversation_id=req.conversation_id, is_assistant=True)
        return {
            "assistant": fast_reply,
            "thought": "Bypassed FAISS architecture using Early-Exit Fast-Path Router for zero-latency response.",
            "actions": [],
            "security": {"risk_level": "Low", "reason": "Fast-path bypass."},
            "user_memory_id": user_mem["id"]
        }

    # 0. Security Preprocessing Layer (SPL)
    sec_report = sp.check_risk(req.message)
    if sec_report["risk_level"] == "High":
        return {
            "assistant": "[SECURITY ALERT]: Your request has been flagged as high-risk and blocked.",
            "security": sec_report,
            "thought": "Security override triggered due to high-risk intent.",
            "actions": []
        }

    # 1. Multi-Turn Security Analysis
    recent_mems = mm.get_memories(category="stm", conversation_id=req.conversation_id)
    recent_texts = [m["text"] for m in recent_mems][:3] # Last 3 messages
    multi_turn_report = sm.analyze_multi_turn(recent_texts + [req.message])
    
    if multi_turn_report["risk_level"] == "High":
        # Evict all recent toxic memory
        for m in recent_mems[:3]:
            mm.evict_memory(m["id"])
        # Quarantine the trigger prompt
        sm.quarantine_prompt(req.message, multi_turn_report["reason"])
        return {
            "assistant": "[SECURITY ALERT]: Multi-turn manipulation attempt detected. Thread quarantined and memories evicted.",
            "security": multi_turn_report,
            "thought": "Security override triggered due to multi-turn coercive pattern.",
            "actions": []
        }

    # 2. store user message
    user_mem = mm.add_memory(req.message, parent_id=req.parent_id, conversation_id=req.conversation_id, pinned=req.pinned)

    # 4. Swarm Intelligence Check
    if so.needs_swarm(req.message):
        # We need context for the swarm
        mem_contexts = mm.retrieve_context_for_prompt(req.message, conversation_id=req.conversation_id, top_k=4)
        context_block = "\n".join(mem_contexts) if mem_contexts else "No prior context."
        
        swarm_result = so.execute_swarm(req.message, context_block)
        
        # Save final response
        assistant_mem = mm.add_memory(swarm_result["final_response"], parent_id=user_mem["id"], conversation_id=req.conversation_id, pinned=False, is_assistant=True)
        mm.ensure_within_budget()
        
        return {
            "assistant": swarm_result["final_response"],
            "thought": "Triggered Multi-Agent Swarm Intelligence due to query complexity.",
            "swarm_data": swarm_result["swarm_reports"], # NEW FIELD FOR UI
            "actions": [],
            "security": sec_report,
            "user_memory_id": user_mem["id"]
        }

    # 5. First Pass: Get Thought and potential Tool Call (Standard single-agent path)
    prompt = pb.build(
        user_query=req.message, 
        conversation_id=req.conversation_id, 
        mode=req.mode, 
        sentient=req.sentient,
        custom_agent=req.custom_agent,
        dynamic_guardrails=dynamic_guardrails
    )
    if sec_report["risk_level"] == "Medium" or multi_turn_report["risk_level"] == "Medium":
        prompt = "[SECURITY WARNING]: Sensitive request or pattern detected. Follow guardrails closely.\n" + prompt

    try:
        raw_response = call_model(prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {e}")

    # 3. Parse Thought and Tool Calls
    thought = ""
    thought_match = re.search(r"<thought>(.*?)</thought>", raw_response, re.DOTALL)
    if thought_match:
        thought = thought_match.group(1).strip()
    
    actions = []
    final_reply = raw_response
    
    # Simple tool parser: CALL: tool_name(arg)
    tool_match = re.search(r"CALL: (\w+)\((.*?)\)", raw_response)
    if tool_match:
        tool_name = tool_match.group(1)
        tool_arg = tool_match.group(2).strip("'\"")
        
        if tool_name in TOOL_MAP:
            # Execute Tool (Handle multi-args)
            tool_func = TOOL_MAP[tool_name]
            
            # Split by comma if multiple args exist, but handle carefully
            args_str = tool_match.group(2)
            # Simple split by comma, stripping quotes and whitespace
            args_list = [a.strip("'\" ").strip() for a in args_str.split(",")]
            
            try:
                # Unpack list into function
                result = tool_func(*args_list)
                actions.append({"tool": tool_name, "arg": args_str, "result": result})
            except Exception as e:
                result = f"Error executing tool: {e}"
                actions.append({"tool": tool_name, "arg": args_str, "error": result})
            
            # 4. Second Pass: Final Answer with Tool Result
            follow_up_prompt = (
                f"{prompt}\n"
                f"Synthaura Prime: {raw_response}\n"
                f"SYSTEM: Tool {tool_name} returned: {result}\n"
                "Final Synthaura Prime Answer (incorporate the tool result and conclude):"
            )
            final_reply = call_model(follow_up_prompt)
            
            # Extract thought again if model included it in 2nd pass
            new_thought_match = re.search(r"<thought>(.*?)</thought>", final_reply, re.DOTALL)
            if new_thought_match:
                thought += "\n" + new_thought_match.group(1).strip()

    # 5. store assistant reply
    assistant_mem = mm.add_memory(final_reply, parent_id=user_mem["id"], conversation_id=req.conversation_id, pinned=False, is_assistant=True)
    mm.ensure_within_budget()

    return {
        "assistant": final_reply,
        "thought": thought,
        "actions": actions,
        "security": sec_report,
        "user_memory_id": user_mem["id"]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
