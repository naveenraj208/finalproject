# llm_client.py
import requests
from config import OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_URL

HEADERS = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}

def call_model(prompt: str, model: str = OPENROUTER_MODEL, max_tokens: int = 512, temperature: float = 0.0):
    """
    Calls OpenRouter chat completion endpoint with a single-user message (compatible with OpenRouter typical shape).
    Adapt as needed to provider response shape.
    """
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not set in .env")

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    resp = requests.post(OPENROUTER_URL, json=payload, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    j = resp.json()
    # expected typical shape: j['choices'][0]['message']['content']
    try:
        content = j.get("choices", [])[0].get("message", {}).get("content")
    except Exception:
        content = None
    if not content:
        # fallback attempt for other shapes
        content = j.get("output") or str(j)
    return content
