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

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from memory_manager import MemoryManager
from prompt_builder import PromptBuilder
from llm_client import call_model

app = FastAPI(title="LLM Memory Backend (safe-mac)")

# single, shared MemoryManager instance
mm = MemoryManager()
pb = PromptBuilder(mm)

class ChatRequest(BaseModel):
    conversation_id: str | None = None
    parent_id: str | None = None
    message: str
    pinned: bool = False

@app.get("/")
def root():
    return {"status": "ok", "note": "Run POST /chat to interact"}

@app.post("/chat")
def chat(req: ChatRequest):
    # 1. store user message
    user_mem = mm.add_memory(req.message, parent_id=req.parent_id, conversation_id=req.conversation_id, pinned=req.pinned)

    # 2. build prompt (context packing)
    prompt = pb.build(req.message, conversation_id=req.conversation_id)

    # 3. call LLM for response
    try:
        ai_text = call_model(prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {e}")

    # 4. store assistant reply as child
    assistant_mem = mm.add_memory(ai_text, parent_id=user_mem["id"], conversation_id=req.conversation_id, pinned=False, is_assistant=True)

    # 5. ensure within budget (compression)
    mm.ensure_within_budget()

    return {
        "assistant": ai_text,
        "user_memory_id": user_mem["id"],
        "assistant_memory_id": assistant_mem["id"]
    }
