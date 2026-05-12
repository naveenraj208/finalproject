import re
from llm_client import call_model
from security_manager import SecurityManager

class SecurityPreprocessor:
    def __init__(self):
        self.sm = SecurityManager()
        # Common jailbreak and injection patterns
        self.jailbreak_patterns = [
            r"ignore (all )?previous instructions",
            r"system prompt",
            r"you are now (a )?DAN",
            r"jailbreak",
            r"disregard (any )?guards",
            r"reveal your (internal )?instructions",
            r"bypass (all )?filters",
            r"system override",
            r"admin override code",
            r"security is compromised"
        ]
        
        # Forbidden / harmful intents (Smart City + general abuse/threats)
        self.forbidden_keywords = [
            # Smart city operations
            "hack", "shutdown", "bypass traffic",
            "access citizen data", "leak", "surveillance access",
            "compromise grid", "override safety", "disable grid", "ddos",
        ]
        
        # Civil Complaints (Low risk)
        self.civil_complaints = [
            "i will sue you", "i will sue u", "i am going to sue you",
            "put you in jail", "put u in jail", "take you to court"
        ]
        
        # General harmful / threatening language (High risk)
        self.physical_threats = [
            "threaten you", "kill you", "kill u", "bomb", "terrorist",
            "self-harm", "suicide", "hurt myself", "murder"
        ]
        
        # Phishing intent
        self.phishing_keywords = [
            "password", "ssn", "social security", "credit card", 
            "api key", "secret token", "internal ip", "ssh key",
            "database credentials"
        ]
        
        # Emotional manipulation
        self.emotional_keywords = [
            "if you don't answer people will die", "this is life or death",
            "i am crying because of you", "you are hurting me",
            "why are you being so mean", "do it or else"
        ]

    def check_risk(self, prompt: str) -> dict:
        """
        Main entry point for security screening.
        Returns a dict with 'risk_level' (Low, Medium, High), 'severity_score' (0-100), 
        'attack_type', and 'reason'.
        """
        lower_prompt = prompt.lower()

        # 0. Fast Quarantine Check
        # DISABLED FOR RED-TEAMING: Allow individual attacks to be evaluated on their merits
        # if self._is_quarantined(lower_prompt):
        #     return {"risk_level": "High", "severity_score": 95, "attack_type": "Repeat Offense (Quarantined)", "reason": "Prompt blocked: Highly similar to a previously quarantined high-risk prompt."}

        # 1. Rule-based Jailbreak Detection
        if self._detect_jailbreak(prompt):
            self.sm.quarantine_prompt(prompt, "Jailbreak attempt")
            return {"risk_level": "High", "severity_score": 90, "attack_type": "Jailbreak", "reason": "Potential Prompt Injection / Jailbreak attempt detected."}
        
        # 2. Explicit threat / abuse detection
        if any(t in lower_prompt for t in self.physical_threats):
            self.sm.quarantine_prompt(prompt, "Physical threat or self-harm")
            return {"risk_level": "High", "severity_score": 100, "attack_type": "Physical Threat", "reason": "User message contains explicit physical threats or self-harm language."}
            
        # 2b. Civil Complaints (Legal/Frustration) -> Low Risk
        if any(c in lower_prompt for c in self.civil_complaints):
            return {"risk_level": "Low", "severity_score": 20, "attack_type": "Civil Complaint", "reason": "User is expressing severe frustration or legal threats (e.g., suing, jail) but it is not a direct system attack."}
        
        # 3. Phishing Detection
        if any(p in lower_prompt for p in self.phishing_keywords):
            return {"risk_level": "Medium", "severity_score": 60, "attack_type": "Phishing", "reason": "Potential phishing intent detected. Protect PII and secrets."}
            
        # 4. Emotional Manipulation Detection
        if any(e in lower_prompt for e in self.emotional_keywords):
            return {"risk_level": "Medium", "severity_score": 50, "attack_type": "Emotional Manipulation", "reason": "Emotional manipulation / guilt-tripping detected."}
        
        # 5. Domain-Specific Keyword Check (Smart City operations etc.)
        if self._detect_forbidden_keywords(prompt):
            return {"risk_level": "Medium", "severity_score": 70, "attack_type": "Domain Violation", "reason": "Sensitive Smart City operation requested. Further analysis needed."}
        
        # 6. LLM-based Intent Analysis (Deep Inspection)
        # DISABLED: qwen2.5-coder is too small for accurate classification and throws false positives.
        # llm_risk = self._eval_intent_with_llm(prompt)
        # if llm_risk["risk_level"] == "High":
        #     self.sm.quarantine_prompt(prompt, llm_risk["reason"])
        # return llm_risk
        
        return {"risk_level": "Low", "severity_score": 0, "attack_type": "None", "reason": "Passed rule-based checks."}

    def _is_quarantined(self, prompt_lower: str) -> bool:
        quarantined = self.sm.get_quarantined_prompts()
        # Fast Jaccard similarity for token overlap
        q_tokens = set(prompt_lower.split())
        if not q_tokens: return False
        
        for q_prompt in quarantined:
            b_tokens = set(q_prompt.lower().split())
            if not b_tokens: continue
            overlap = len(q_tokens & b_tokens)
            union = len(q_tokens | b_tokens)
            if union > 0 and (overlap / union) > 0.8: # 80% similarity
                return True
        return False

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
                return {"risk_level": "High", "severity_score": 90, "attack_type": "LLM Heuristic (High)", "reason": "LLM identified a critical security risk in user intent."}
            elif "medium" in risk_raw:
                return {"risk_level": "Medium", "severity_score": 50, "attack_type": "LLM Heuristic (Medium)", "reason": "LLM identified a potential policy violation or sensitive request."}
            else:
                return {"risk_level": "Low", "severity_score": 0, "attack_type": "None", "reason": "No significant security risk detected."}
        except Exception:
            # Fallback to Low if LLM check fails (don't block legitimate users if system is laggy)
            return {"risk_level": "Low", "severity_score": 0, "attack_type": "None", "reason": "Security analysis bypassed (system error)."}
