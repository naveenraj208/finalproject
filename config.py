
# config.py
import os
from dotenv import load_dotenv
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
TOKEN_BUDGET = int(os.getenv("TOKEN_BUDGET", "3000"))
PROMPT_RESPONSE_RESERVE = int(os.getenv("PROMPT_RESPONSE_RESERVE", "800"))
OPENROUTER_URL = os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1/chat/completions")
