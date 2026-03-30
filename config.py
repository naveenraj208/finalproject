
# config.py
import os
from dotenv import load_dotenv
load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b-instruct-q4_k_m")
TOKEN_BUDGET = int(os.getenv("TOKEN_BUDGET", "3000"))
PROMPT_RESPONSE_RESERVE = int(os.getenv("PROMPT_RESPONSE_RESERVE", "800"))
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
FAISS_INDEX_PATH = "knowledge.index"
KB_META_DB_PATH = "kb_meta.db"
