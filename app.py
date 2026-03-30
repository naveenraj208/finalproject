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

app = FastAPI(title="LLM Memory Backend (safe-mac)")

from security_preprocessor import SecurityPreprocessor

# single, shared instance
mm = MemoryManager()
pb = PromptBuilder(mm)
sp = SecurityPreprocessor()

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

@app.post("/chat")
def chat(req: ChatMessage):
    # -1. Fast-Path Intent Router (Bypass RAG/Tooling for speed)
    query_lower = req.message.lower().strip()
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

    # 1. store user message
    user_mem = mm.add_memory(req.message, parent_id=req.parent_id, conversation_id=req.conversation_id, pinned=req.pinned)

    # 2. First Pass: Get Thought and potential Tool Call
    prompt = pb.build(
        user_query=req.message, 
        conversation_id=req.conversation_id, 
        mode=req.mode, 
        sentient=req.sentient,
        custom_agent=req.custom_agent
    )
    if sec_report["risk_level"] == "Medium":
        prompt = "[SECURITY WARNING]: Sensitive request detected.\n" + prompt

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
