# main.py
import sqlite3
import uuid
import time
from typing import Optional, List, Dict, Set, Tuple
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import math
import json
import re
from datetime import datetime, timezone
from summarizer import textrank_summary
import json, uuid
from sentence_transformers import SentenceTransformer
import numpy as np
embed_model = SentenceTransformer("all-MiniLM-L6-v2")



# ---------------------------
# Basic Tokenizer (robust fallback)
# ---------------------------
class Tokenizer:
    """
    Token counter abstraction. Tries to use tiktoken if installed (recommended),
    otherwise uses a deterministic fallback (word/token-ish heuristic).
    """

    def __init__(self):
        try:
            import tiktoken  # type: ignore
            self._tiktoken = tiktoken
            # default encoding - try cl100k_base if available
            try:
                self.enc = tiktoken.get_encoding("cl100k_base")
            except Exception:
                self.enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
            self._use_tiktoken = True
        except Exception:
            self._tiktoken = None
            self._use_tiktoken = False

    def count(self, text: str) -> int:
        if not text:
            return 0
        if self._use_tiktoken:
            try:
                return len(self.enc.encode(text))
            except Exception:
                # fallback to safe heuristic
                pass
        # Heuristic tokenization:
        # split on whitespace & punctuation clusters -> deterministic and conservative
        tokens = re.findall(r"\w+|[^\s\w]", text, flags=re.UNICODE)
        return max(1, len(tokens))


tokenizer = Tokenizer()

# ---------------------------
# DB Helper (SQLite)
# ---------------------------
DB_PATH = "memory_store.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        title TEXT,
        created_at REAL
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        conversation_id TEXT,
        parent_id TEXT,
        sender TEXT,
        content TEXT,
        tokens INTEGER,
        importance REAL,
        pinned INTEGER,
        metadata TEXT,
        created_at REAL,
        priority REAL,
        thread_depth INTEGER,
        FOREIGN KEY(conversation_id) REFERENCES conversations(id)
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS summaries (
        id TEXT PRIMARY KEY,
        conversation_id TEXT,
        source_message_ids TEXT,  -- JSON list of message IDs summarized
        summary_text TEXT,
        tokens INTEGER,
        level TEXT,               -- 'mid' or 'long'
        created_at REAL
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS embeddings (
        message_id TEXT PRIMARY KEY,
        conversation_id TEXT,
        vector BLOB
    )
    """)
    



    conn.commit()
    conn.close()

init_db()

# ---------------------------
# Pydantic models for API
# ---------------------------
class CreateConversation(BaseModel):
    title: Optional[str] = "Conversation"

class CreateMessage(BaseModel):
    conversation_id: str
    parent_id: Optional[str] = None
    sender: str = "user"  # user/assistant/system
    content: str
    importance: Optional[float] = Field(0.5, ge=0.0, le=1.0)
    pinned: Optional[bool] = False
    metadata: Optional[Dict] = None

class UpdateMessage(BaseModel):
    content: Optional[str] = None
    importance: Optional[float] = None
    pinned: Optional[bool] = None
    metadata: Optional[Dict] = None

# ---------------------------
# Utilities
# ---------------------------
def now_ts() -> float:
    return time.time()

def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()

# ---------------------------
# Message / Priority Logic
# ---------------------------
def compute_thread_depth(conn, msg_parent_id: Optional[str]) -> int:
    """
    Compute depth by walking parents.
    """
    depth = 0
    cur = conn.cursor()
    pid = msg_parent_id
    while pid:
        cur.execute("SELECT parent_id FROM messages WHERE id = ?", (pid,))
        row = cur.fetchone()
        if not row:
            break
        pid = row["parent_id"]
        depth += 1
    return depth

def count_children(conn, message_id: str) -> int:
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as c FROM messages WHERE parent_id = ?", (message_id,))
    row = cur.fetchone()
    return row["c"] if row else 0

# priority components explained in the docstring below
def compute_priority(conn, message_row) -> float:
    """
    Deterministic priority scoring (0..1). Components:
      - pinned (binary, high weight)
      - explicit importance (0..1 user-provided)
      - recency (exponential decay)
      - reply_count influence (more replies -> higher priority)
      - thread_depth (slight boost for deeper nodes)
    The exact formula is normalized weighted sum and clamped to [0,1].
    """
    weights = {
        "pinned": 3.0,
        "importance": 2.0,
        "recency": 1.5,
        "reply_count": 1.0,
        "thread_depth": 0.5
    }
    total_w = sum(weights.values())

    pinned = 1.0 if message_row["pinned"] else 0.0
    explicit_imp = float(message_row["importance"]) if message_row["importance"] is not None else 0.5

    # recency: exponential decay with half-life H seconds
    H = 60.0 * 60.0 * 24.0 * 7.0  # half-life = 7 days (configurable)
    age = max(0.0, now_ts() - float(message_row["created_at"]))
    recency_score = math.exp(-math.log(2) * (age / H))  # in (0,1]

    reply_count = count_children(conn, message_row["id"])
    reply_score = math.tanh(reply_count * 0.5)  # maps to (0,1)

    thread_depth = float(message_row["thread_depth"] or 0)
    # normalize depth influence via logistic: deeper threads -> slight boost, bounded.
    depth_score = 1.0 - 1.0 / (1.0 + 0.2 * thread_depth)

    # Combine
    raw = (
        weights["pinned"] * pinned +
        weights["importance"] * explicit_imp +
        weights["recency"] * recency_score +
        weights["reply_count"] * reply_score +
        weights["thread_depth"] * depth_score
    )
    priority = raw / total_w
    # clamp
    priority = max(0.0, min(1.0, priority))
    return priority

# ---------------------------
# DB operations
# ---------------------------
def create_conversation(title: str = "Conversation") -> Dict:
    conn = get_conn()
    cid = str(uuid.uuid4())
    ts = now_ts()
    conn.execute("INSERT INTO conversations (id, title, created_at) VALUES (?, ?, ?)", (cid, title, ts))
    conn.commit()
    conn.close()
    return {"id": cid, "title": title, "created_at": ts}

def upsert_message(msg: CreateMessage) -> Dict:
    conn = get_conn()
    cur = conn.cursor()
    # validate conversation exists
    cur.execute("SELECT id FROM conversations WHERE id = ?", (msg.conversation_id,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Conversation not found")

    msg_id = str(uuid.uuid4())
    ts = now_ts()
    tokens = tokenizer.count(msg.content)
    thread_depth = compute_thread_depth(conn, msg.parent_id)
    pinned_i = 1 if msg.pinned else 0
    metadata_json = json.dumps(msg.metadata or {})
    # temporary insert with placeholder priority; we'll compute precise priority next
    cur.execute("""
      INSERT INTO messages (id, conversation_id, parent_id, sender, content, tokens, importance, pinned, metadata, created_at, priority, thread_depth)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (msg_id, msg.conversation_id, msg.parent_id, msg.sender, msg.content, tokens, float(msg.importance), pinned_i, metadata_json, ts, 0.0, thread_depth))
    conn.commit()
    # --- NEW: store semantic embedding for retrieval ---
    try:
        vec = embed_model.encode(msg.content).astype(np.float32).tobytes()
        cur.execute(
            "INSERT OR REPLACE INTO embeddings (message_id, conversation_id, vector) VALUES (?, ?, ?)",
            (msg_id, msg.conversation_id, vec)
        )
        conn.commit()
    except Exception as e:
        print("Embedding insert failed:", e)
# ---------------------------------------------------

    # compute priority deterministically now
    cur.execute("SELECT * FROM messages WHERE id = ?", (msg_id,))
    row = cur.fetchone()
    priority = compute_priority(conn, row)
    cur.execute("UPDATE messages SET priority = ? WHERE id = ?", (priority, msg_id))
    conn.commit()
    cur.execute("SELECT * FROM messages WHERE id = ?", (msg_id,))
    out = dict(cur.fetchone())
    conn.close()
    # convert types
    out["pinned"] = bool(out["pinned"])
    out["metadata"] = json.loads(out["metadata"] or "{}")
    return out

def update_message(msg_id: str, upd: UpdateMessage) -> Dict:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM messages WHERE id = ?", (msg_id,))
    r = cur.fetchone()
    if not r:
        conn.close()
        raise HTTPException(status_code=404, detail="Message not found")
    data = dict(r)
    # update fields
    if upd.content is not None:
        tokens = tokenizer.count(upd.content)
        cur.execute("UPDATE messages SET content = ?, tokens = ? WHERE id = ?", (upd.content, tokens, msg_id))
    if upd.importance is not None:
        cur.execute("UPDATE messages SET importance = ? WHERE id = ?", (float(upd.importance), msg_id))
    if upd.pinned is not None:
        cur.execute("UPDATE messages SET pinned = ? WHERE id = ?", (1 if upd.pinned else 0, msg_id))
    if upd.metadata is not None:
        cur.execute("UPDATE messages SET metadata = ? WHERE id = ?", (json.dumps(upd.metadata), msg_id))
    conn.commit()
    cur.execute("SELECT * FROM messages WHERE id = ?", (msg_id,))
    row = cur.fetchone()
    # recompute priority (priority is deterministic)
    priority = compute_priority(conn, row)
    cur.execute("UPDATE messages SET priority = ? WHERE id = ?", (priority, msg_id))
    conn.commit()
    cur.execute("SELECT * FROM messages WHERE id = ?", (msg_id,))
    out = dict(cur.fetchone())
    out["pinned"] = bool(out["pinned"])
    out["metadata"] = json.loads(out["metadata"] or "{}")
    conn.close()
    return out

def list_conversation_messages(conversation_id: str) -> List[Dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC", (conversation_id,))
    rows = cur.fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["pinned"] = bool(d["pinned"])
        d["metadata"] = json.loads(d["metadata"] or "{}")
        out.append(d)
    conn.close()
    return out
def retrieve_similar_messages(conversation_id: str, query_text: str, top_k: int = 5):
    """Return top-k most semantically similar messages for a query text."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT message_id, vector FROM embeddings WHERE conversation_id = ?", (conversation_id,))
    rows = cur.fetchall()
    if not rows:
        conn.close()
        return []

    query_vec = embed_model.encode(query_text)
    sims = []
    for r in rows:
        v = np.frombuffer(r["vector"], dtype=np.float32)
        sim = np.dot(query_vec, v) / (np.linalg.norm(query_vec) * np.linalg.norm(v))
        sims.append((r["message_id"], float(sim)))

    sims.sort(key=lambda x: x[1], reverse=True)
    top_ids = [sid for sid, _ in sims[:top_k]]

    placeholders = ",".join(["?"] * len(top_ids))
    cur.execute(f"SELECT * FROM messages WHERE id IN ({placeholders})", tuple(top_ids))
    res = [dict(x) for x in cur.fetchall()]
    conn.close()
    return res

# ---------------------------
# Tree and DP selection logic
# ---------------------------

class Node:
    def __init__(self, row):
        self.id = row["id"]
        self.parent_id = row["parent_id"]
        self.tokens = int(row["tokens"])
        self.priority = float(row["priority"])
        self.created_at = float(row["created_at"])
        self.content = row["content"]
        self.children: List['Node'] = []
        # Keep original row if needed
        self.row = row

def build_forest(rows: List[sqlite3.Row]) -> Tuple[Dict[str, Node], List[Node]]:
    nodes: Dict[str, Node] = {}
    for r in rows:
        nodes[r["id"]] = Node(r)
    roots: List[Node] = []
    for n in nodes.values():
        pid = n.parent_id
        if pid and pid in nodes:
            nodes[pid].children.append(n)
        else:
            roots.append(n)
    return nodes, roots

def dp_for_node(node: Node, max_tokens: int) -> Dict[int, Tuple[float, Set[str]]]:
    """
    Returns a dict: cost_tokens -> (priority_sum, set_of_message_ids)
    For each node, options:
      - exclude node entirely: cost 0, priority 0
      - include node: cost node.tokens + costs from selecting any combination of children (children only selectable if parent included).
    We compute all feasible costs up to max_tokens.
    """
    # Base: start with included set being just the node
    # We'll recursively compute child's dp to convolve
    child_dps = [dp_for_node(child, max_tokens) for child in node.children]

    # When parent is excluded, children cannot be included (by design)
    exclude_option = {0: (0.0, set())}

    # compute included options: start with node itself
    included_base_cost = node.tokens
    if included_base_cost > max_tokens:
        # cannot include node at all within budget
        included_options = {}
    else:
        # Start with node only
        included_options = {included_base_cost: (node.priority, {node.id})}

        # For each child, convolve included_options with child's options
        for child_dp in child_dps:
            # child_dp dict: cost -> (priority, set)
            new_options: Dict[int, Tuple[float, Set[str]]] = {}
            # For the parent included case, for each child we may choose any child's dp option (0 or include child's subtree)
            # But child_dp already contains the "exclude child" option at cost 0.
            for cost_parent, (pri_parent, set_parent) in included_options.items():
                for cost_child, (pri_child, set_child) in child_dp.items():
                    new_cost = cost_parent + cost_child
                    if new_cost > max_tokens:
                        continue
                    new_pri = pri_parent + pri_child
                    new_set = set_parent.union(set_child)
                    existing = new_options.get(new_cost)
                    if (existing is None) or (new_pri > existing[0]):
                        new_options[new_cost] = (new_pri, new_set)
            included_options = new_options

    # Merge exclude option and included_options; For each cost keep the best priority
    merged: Dict[int, Tuple[float, Set[str]]] = {}
    # start with exclude
    for c, v in exclude_option.items():
        merged[c] = v
    for c, v in included_options.items():
        existing = merged.get(c)
        if (existing is None) or (v[0] > existing[0]):
            merged[c] = v
    # Optionally prune dominated entries: keep only (cost -> max priority)
    # reduction: for increasing cost ensure monotonicity
    costs_sorted = sorted(merged.keys())
    best = -1.0
    pruned = {}
    for c in costs_sorted:
        pri, s = merged[c]
        if pri > best:
            pruned[c] = (pri, s)
            best = pri
    return pruned

def combine_roots_dp(roots: List[Node], max_tokens: int) -> Dict[int, Tuple[float, Set[str]]]:
    """
    Combine DP tables from independent roots (forest knapsack).
    """
    dp_total = {0: (0.0, set())}
    for root in roots:
        dp_root = dp_for_node(root, max_tokens)
        new_total = {}
        for cost_a, (pri_a, set_a) in dp_total.items():
            for cost_b, (pri_b, set_b) in dp_root.items():
                new_cost = cost_a + cost_b
                if new_cost > max_tokens:
                    continue
                new_pri = pri_a + pri_b
                new_set = set_a.union(set_b)
                existing = new_total.get(new_cost)
                if (existing is None) or (new_pri > existing[0]):
                    new_total[new_cost] = (new_pri, new_set)
        # prune monotonic
        costs_sorted = sorted(new_total.keys())
        best = -1.0
        pruned = {}
        for c in costs_sorted:
            pri, s = new_total[c]
            if pri > best:
                pruned[c] = (pri, s)
                best = pri
        dp_total = pruned
    return dp_total

def select_messages_exact(conversation_id: str, token_budget: int) -> List[str]:
    """
    Build forest for a conversation, run exact DP, return best set of message IDs for token_budget.
    Deterministic and respects parent->child inclusion rule.
    """
    rows = list_conversation_messages(conversation_id)
    if not rows:
        return []
    # convert rows to sqlite3.Row-like objects, Node builder expects row dict style; we'll craft simple objects
    # We'll re-query DB to get sqlite rows for Node
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC", (conversation_id,))
    rows = cur.fetchall()
    nodes_map, roots = build_forest(rows)
    # if token_budget < 1 return empty
    if token_budget < 1:
        return []
    dp_total = combine_roots_dp(roots, token_budget)
    if not dp_total:
        return []
    # choose best priority among costs <= token_budget
    best_cost = max(dp_total.keys(), key=lambda c: (dp_total[c][0], -c))
    best_set = dp_total[best_cost][1]
    # return sorted list of message ids in chronological order
    # we want coherence: sort by created_at ascending
    selected_rows = []
    cur.execute("SELECT id, created_at FROM messages WHERE id IN ({seq})".format(seq=",".join(["?"]*len(best_set))), tuple(best_set))
    sel = cur.fetchall()
    sel_sorted = sorted(sel, key=lambda r: r["created_at"])
    conn.close()
    return [r["id"] for r in sel_sorted]

# ---------------------------
# Prompt construction
# ---------------------------
def build_context_prompt(conversation_id: str, token_budget: int) -> Dict:
    """
    Returns:
      { "selected_messages": [ {id, sender, content, created_at, tokens} ... ],
        "total_tokens": int,
        "priority_sum": float,
        "raw_prompt_text": str }
    The prompt text concatenates messages preserving chronological order. Inserts simple separators.
    """
    selected_ids = select_messages_exact(conversation_id, token_budget)
    if not selected_ids:
        return {"selected_messages": [], "total_tokens": 0, "priority_sum": 0.0, "raw_prompt_text": ""}
    conn = get_conn()
    cur = conn.cursor()
    placeholders = ",".join("?" for _ in selected_ids)
    cur.execute(f"SELECT * FROM messages WHERE id IN ({placeholders}) ORDER BY created_at ASC", tuple(selected_ids))
    rows = cur.fetchall()
    total_tokens = 0
    priority_sum = 0.0
    msg_list = []
    for r in rows:
        msg = dict(r)
        msg_list.append({
            "id": msg["id"],
            "sender": msg["sender"],
            "content": msg["content"],
            "created_at": msg["created_at"],
            "tokens": msg["tokens"],
            "priority": msg["priority"]
        })
        total_tokens += int(msg["tokens"])
        priority_sum += float(msg["priority"])
    # Build a simple prompt structure that keeps each message clearly labeled to avoid conflation
    pieces = []
    for m in msg_list:
        ts = datetime.fromtimestamp(m["created_at"], tz=timezone.utc).isoformat()
        pieces.append(f"[{m['sender'].upper()} | {ts} | tokens={m['tokens']}] {m['content']}")
    raw_prompt_text = "\n\n".join(pieces)
    conn.close()
    return {"selected_messages": msg_list, "total_tokens": total_tokens, "priority_sum": priority_sum, "raw_prompt_text": raw_prompt_text}


def summarize_old_context(conversation_id: str, token_threshold: int = 2000):
    """
    Compresses low-priority or older messages once conversation exceeds token_threshold.
    Saves a deterministic extractive summary.
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC", (conversation_id,))
    rows = cur.fetchall()
    if not rows:
        conn.close()
        return None

    total_tokens = sum(r["tokens"] for r in rows)
    if total_tokens < token_threshold:
        conn.close()
        return None

    # Pick low-priority messages for summarization
    low_priority = [r for r in rows if r["priority"] < 0.5]
    if not low_priority:
        conn.close()
        return None

    combined_text = "\n".join(r["content"] for r in low_priority)
    summary = textrank_summary(combined_text, compression_ratio=0.25)
    summary_tokens = tokenizer.count(summary)

    sid = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO summaries (id, conversation_id, source_message_ids, summary_text, tokens, level, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (sid, conversation_id, json.dumps([r["id"] for r in low_priority]), summary, summary_tokens, 'mid', time.time()))
    conn.commit()
    conn.close()
    return {"summary_id": sid, "tokens": summary_tokens, "compressed": len(low_priority)}


# ---------------------------
# FastAPI app
# ---------------------------
app = FastAPI(title="Phase1 Memory Manager (Deterministic)")

@app.post("/conversations")
def api_create_conversation(req: CreateConversation):
    c = create_conversation(req.title)
    return c

@app.post("/messages")
def api_create_message(req: CreateMessage):
    m = upsert_message(req)
    return m

@app.patch("/messages/{msg_id}")
def api_update_message(msg_id: str, upd: UpdateMessage):
    return update_message(msg_id, upd)

@app.get("/conversations/{conversation_id}/messages")
def api_list_messages(conversation_id: str):
    return list_conversation_messages(conversation_id)


@app.get("/conversations/{conversation_id}/prompt")
def api_get_prompt(conversation_id: str, token_budget: int = 1024, query: str = None):
    # Auto-summarize if large
    summarize_old_context(conversation_id)

    # Select core context (Phase 1)
    prompt = build_context_prompt(conversation_id, token_budget)

    # --- Phase 2 summaries ---
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM summaries WHERE conversation_id = ? ORDER BY created_at ASC", (conversation_id,))
    summaries = cur.fetchall()
    conn.close()

    remaining = token_budget - prompt["total_tokens"]
    included = []
    for s in summaries:
        if s["tokens"] <= remaining:
            included.append(dict(s))
            remaining -= s["tokens"]

    # --- Phase 3: semantic recall if query provided ---
    retrieved = []
    if query:
        retrieved = retrieve_similar_messages(conversation_id, query, top_k=3)
        # include only if still room
        for r in retrieved:
            t = r["tokens"]
            if t <= remaining:
                included.append(r)
                remaining -= t

    # combine all text
    text_blocks = [prompt["raw_prompt_text"]]
    for sm in included:
        if "summary_text" in sm:
            text_blocks.append(f"[SUMMARY] {sm['summary_text']}")
        else:
            text_blocks.append(f"[RETRIEVED] {sm['content']}")
    combined_text = "\n\n".join(text_blocks)
    total_tokens = tokenizer.count(combined_text)

    return {
        "selected_messages": prompt["selected_messages"],
        "summaries": [s for s in included if "summary_text" in s],
        "retrieved": [r for r in included if "content" in r and "summary_text" not in r],
        "total_tokens": total_tokens,
        "raw_prompt_text": combined_text
    }

@app.get("/conversations/{conversation_id}/retrieve")
def api_retrieve(conversation_id: str, query: str, top_k: int = 5):
    """Semantic search within a conversation."""
    return retrieve_similar_messages(conversation_id, query, top_k)


# ---------------------------
# Demo script that runs if module executed directly
# ---------------------------
def demo_workflow():
    print("=== Demo: Create conversation and messages with parent-child relations ===")
    c = create_conversation("Phase1 Demo")
    cid = c["id"]
    print("Created conversation:", cid)
    # Add root messages
    m1 = CreateMessage(conversation_id=cid, parent_id=None, sender="user", content="Project goal: build adaptive memory.", importance=0.9, pinned=True)
    r1 = upsert_message(m1)
    print("Added root m1:", r1["id"])
    # Add child
    m2 = CreateMessage(conversation_id=cid, parent_id=r1["id"], sender="assistant", content="Acknowledged. I'll store core goals as pinned.", importance=0.8)
    r2 = upsert_message(m2)
    print("Added child m2:", r2["id"])
    # Another thread
    m3 = CreateMessage(conversation_id=cid, parent_id=None, sender="user", content="Small note: remember my preference - cards black.", importance=0.7)
    r3 = upsert_message(m3)
    print("Added m3:", r3["id"])
    # Child under m3
    m4 = CreateMessage(conversation_id=cid, parent_id=r3["id"], sender="assistant", content="Okay, UI color set to black in metadata.", importance=0.6)
    r4 = upsert_message(m4)
    print("Added m4:", r4["id"])
    # Deeper child to test chain
    m5 = CreateMessage(conversation_id=cid, parent_id=r2["id"], sender="user", content="Also ensure token budget selection keeps parents.", importance=0.6)
    r5 = upsert_message(m5)
    print("Added m5:", r5["id"])

    # Show all messages
    all_msgs = list_conversation_messages(cid)
    print("\nAll messages:")
    for mm in all_msgs:
        print(f"- {mm['id']} pid={mm['parent_id']} tokens={mm['tokens']} priority={mm['priority']:.3f} pinned={mm['pinned']} depth={mm['thread_depth']}")

    # Now request a tiny token budget so only highest-value messages included
    print("\nBuild prompt for token_budget=40 (tight):")
    res = build_context_prompt(cid, token_budget=40)
    print("Selected total tokens:", res["total_tokens"], "priority_sum:", res["priority_sum"])
    print(res["raw_prompt_text"])

    print("\nBuild prompt for token_budget=500 (larger):")
    res2 = build_context_prompt(cid, token_budget=500)
    print("Selected total tokens:", res2["total_tokens"], "priority_sum:", res2["priority_sum"])
    print(res2["raw_prompt_text"])
# inside main.py
def log_metrics(conversation_id: str, tokens_before: int, tokens_after: int, relevant_retrieved: int):
    ratio = tokens_before / max(tokens_after, 1)
    print(f"Compression ratio: {ratio:.2f} | Relevant items: {relevant_retrieved}")

if __name__ == "__main__":
    # Run demo for standalone testing
    demo_workflow()
    # For API instead, comment the line above and uncomment below:
    # import uvicorn
    # uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
