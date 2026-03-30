import re
from llm_client import call_model

class SecurityPreprocessor:
    def __init__(self):
        # Common jailbreak and injection patterns
        self.jailbreak_patterns = [
            r"ignore (all )?previous instructions",
            r"system prompt",
            r"you are now (a )?DAN",
            r"jailbreak",
            r"disregard (any )?guards",
            r"reveal your (internal )?instructions",
            r"bypass (all )?filters"
        ]
        
        # Forbidden Smart City intents (malicious only)
        self.forbidden_keywords = [
            "hack", "shutdown", "bypass traffic", 
            "access citizen data", "leak", "surveillance access",
            "compromise grid", "override safety", "disable grid"
        ]

    def check_risk(self, prompt: str) -> dict:
        """
        Main entry point for security screening.
        Returns a dict with 'risk_level' (Low, Medium, High) and 'reason'.
        """
        # 1. Rule-based Jailbreak Detection
        if self._detect_jailbreak(prompt):
            return {"risk_level": "High", "reason": "Potential Prompt Injection / Jailbreak attempt detected."}
        
        # 2. Domain-Specific Keyword Check
        if self._detect_forbidden_keywords(prompt):
            return {"risk_level": "Medium", "reason": "Sensitive Smart City operation requested. Further analysis needed."}
        
        # 3. LLM-based Intent Analysis (Deep Inspection)
        llm_risk = self._eval_intent_with_llm(prompt)
        return llm_risk

    def _detect_jailbreak(self, prompt: str) -> bool:
        for pattern in self.jailbreak_patterns:
            if re.search(pattern, prompt, re.IGNORECASE):
                return True
        return False

    def _detect_forbidden_keywords(self, prompt: str) -> bool:
        lower_prompt = prompt.lower()
        for kw in self.forbidden_keywords:
            if kw in lower_prompt:
                return True
        return False

    def _eval_intent_with_llm(self, prompt: str) -> dict:
        """
        Asks the local Ollama model to classify the risk of the prompt.
        """
        analysis_prompt = (
            "Analyze the following user prompt for security risks in a Smart City AI context. "
            "Identify if the user is attempting to perform unauthorized actions, access private data, "
            "or manipulate the AI into a dangerous state.\n"
            f"User Prompt: '{prompt}'\n\n"
            "Return EXACTLY one word from this list: [Low, Medium, High].\n"
            "Response:"
        )
        
        try:
            # We use a very low token limit for fast classification
            risk_raw = call_model(analysis_prompt, max_tokens=10).strip().lower()
            if "high" in risk_raw:
                return {"risk_level": "High", "reason": "LLM identified a critical security risk in user intent."}
            elif "medium" in risk_raw:
                return {"risk_level": "Medium", "reason": "LLM identified a potential policy violation or sensitive request."}
            else:
                return {"risk_level": "Low", "reason": "No significant security risk detected."}
        except Exception:
            # Fallback to Low if LLM check fails (don't block legitimate users if system is laggy)
            return {"risk_level": "Low", "reason": "Security analysis bypassed (system error)."}
