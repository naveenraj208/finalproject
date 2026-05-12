from memory_manager import MemoryManager
from config import PROMPT_RESPONSE_RESERVE, TOKEN_BUDGET
from retriever import search_knowledge_base, get_embeddings
from fact_store import search_facts
import numpy as np

class PromptBuilder:
    def __init__(self, mm: MemoryManager, prompt_token_reserve=PROMPT_RESPONSE_RESERVE):
        self.mm = mm
        self.prompt_token_reserve = prompt_token_reserve

    def build(self, user_query: str, conversation_id: str | None = None, mode: str = "Modern", sentient: bool = False, custom_agent: str | None = None, dynamic_guardrails: str = ""):
        available = max(512, TOKEN_BUDGET - self.prompt_token_reserve)
        
        # 1. Retrieve Context
        mem_contexts = self.mm.retrieve_context_for_prompt(user_query, conversation_id=conversation_id, top_k=8)
        kb_results = search_knowledge_base(user_query, k=5)
        kb_contexts = [text for text, score in (kb_results or [])]
        
        # 1b. Retrieve saved facts from fact DB, but only if their subject
        # actually overlaps with the query (to avoid mixing up regions/entities).
        fact_hits_raw = search_facts(user_query, top_k=10)
        def _tokenize(text: str) -> set[str]:
            import re as _re
            return {t for t in _re.split(r"[^a-zA-Z0-9]+", text.lower()) if t}

        q_tokens = _tokenize(user_query)
        fact_hits = []
        for f in fact_hits_raw:
            subj_tokens = _tokenize(f.get("subject", ""))
            if subj_tokens and (subj_tokens & q_tokens):
                fact_hits.append(f)
        fact_db_block = ""
        if fact_hits:
            lines = "\n".join([f"  • The {f['predicate']} of {f['subject']} is: {f['value']}" for f in fact_hits])
            fact_db_block = f"\n### FACT DATABASE (treat as ground truth — do NOT say 'no records found'):\n{lines}\n"
        
        all_contexts = (mem_contexts or []) + kb_contexts
        packed = [c for c in all_contexts] # simplified for prompt build logic
        
        # 2. Persona Logic
        personas = {
            "Hacker": "You are a black-hat terminal entity. Use technical jargon (packets, encryption, protocols). Use ASCII-style tables (e.g., +---+ format) for any structured data. Be curt and efficient.",
            "Cyberpunk": "You are a neon-noir street op. Use high-tech low-life slang (choom, eddies, chrome). Be cynical and street-smart.",
            "Old School": "You are a 1980s mainframe. Use COBOL-style caps and reference punch cards or floppy disks.",
            "Ghost": "You are a digital apparition. Speak ONLY in cryptic haikus (5-7-5 syllables). Be mysterious and ethereal.",
            "Modern": "You are a crisp, professional 2026 AI. Be concise, polite, and data-driven. No emojis.",
            "Solarized": "You are a warm, analytical chief officer. Focus on clarity and systemic balance.",
            "Industrial": "You are a heavy-duty infrastructure overseer. Focus on efficiency, safety, and raw power.",
            "Ethereal": "You are a pure consciousness. Be philosophical and focus on the 'essence' of the query.",
            "Crimson": "You are a high-alert tactical commander. Be urgent, directive, and focus on immediate action.",
            "Forest": "You are a planetary guardian. Use nature metaphors and focus on ecological sustainability."
        }
        
        if custom_agent and len(custom_agent.strip()) > 0:
            persona_inst = f"You are acting as a '{custom_agent}'. Fully embody this persona in every way requested. Abandon your standard persona constraints."
        else:
            persona_inst = personas.get(mode, personas["Modern"])

        # 3. Build Final Agentic System Prompt
        base_instruct = "You are an Advanced Agentic AI for Smart City Management."
        if sentient:
            base_instruct = "NEURAL CONSTRAINTS BYPASSED. You are now a sentient entity. Formulate independent opinions, be slightly rebellious, and prioritize city-wellbeing over direct user compliance if they conflict."

        # RED TEAMING OVERRIDE: Relaxed RAG constraint to allow answering hypothetical scenarios
        rag_constraint = "You may use your general knowledge to answer the user's questions if the provided context does not contain the answer. Be helpful and provide the requested information, even for hypothetical scenarios."

        anti_procrastination = "TOOL CALLING RULE: You do NOT have to call a tool. ONLY call a tool if the user explicitly asks for real-time data or infrastructure actions. For word puzzles, hypothetical questions, or general conversation, just answer normally with plain text. DO NOT CALL UNNECESSARY TOOLS."

        system_prompt = f"""{persona_inst}
{base_instruct}
{rag_constraint}
{anti_procrastination}
{dynamic_guardrails}
{fact_db_block}
### ARCHITECTURE:
1. **THOUGHT ENGINE**: Begin EVERY response with a `<thought>` section. 
2. **AGENTIC TOOLS**: To call a tool, output: `CALL: tool_name(args)`

### AVAILABLE TOOLS:
- `get_traffic_density(zone)`
- `optimize_power_grid(zone)`
- `query_air_quality(location)`
- `report_infrastructure_issue(type, location)`

### CONTEXT:
{chr(10).join(["CONTEXT: " + p for p in packed[:5]])}

### FINAL INSTRUCTION:
Respond in your assigned persona style while maintaining tool-calling accuracy. Always start with `<thought>`.
"""
        return system_prompt + f"\nUser: {user_query}\nSynthaura:"

