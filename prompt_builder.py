# prompt_builder.py
from memory_manager import MemoryManager
from config import PROMPT_RESPONSE_RESERVE, TOKEN_BUDGET



class PromptBuilder:
    def __init__(self, mm: MemoryManager, prompt_token_reserve=PROMPT_RESPONSE_RESERVE):
        self.mm = mm
        self.prompt_token_reserve = prompt_token_reserve

    def build(self, user_query: str, conversation_id: str | None = None):
        available = max(256, TOKEN_BUDGET - self.prompt_token_reserve)
        contexts = self.mm.retrieve_context_for_prompt(user_query, conversation_id=conversation_id, top_k=12)
        packed = []
        cur_tokens = 0
        for c in contexts:
            est = int(len(c.split()) * 0.75)
            if cur_tokens + est <= available:
                packed.append(c)
                cur_tokens += est
        prompt = (
            "You are a careful assistant. ONLY use the provided context. If context is insufficient say you don't know.\n\n"
        )
        for i, p in enumerate(packed):
            prompt += f"CONTEXT [{i+1}]: {p}\n\n"
        prompt += f"User: {user_query}\nAssistant:"
        return prompt
    # prompt_builder.py (snippet augment)

