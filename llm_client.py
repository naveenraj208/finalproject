# llm_client.py
import requests
from config import OLLAMA_URL, OLLAMA_MODEL

def call_model(prompt: str, model: str = OLLAMA_MODEL, max_tokens: int = 512, temperature: float = 0.0):
    """
    Calls local Ollama API for generation.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": temperature
        }
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
    resp.raise_for_status()
    j = resp.json()
    return j.get("response", "")
