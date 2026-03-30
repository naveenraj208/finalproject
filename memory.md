# Advanced Memory & RAG Subsystem (`memory.md`)

The memory engine (`memory_manager.py`) is standardly considered the most complex processing layer within Synthaura Prime. It orchestrates real-time conversational states against historical vectorized storage seamlessly.

## 1. Database Architecture
Memory instances are fundamentally mapped into a persistent `SQLite` data table utilizing `SQLAlchemy`. 
The `MemoryRow` Schema:
*   `id`: UUID tracking.
*   `text`: The raw human/assistant string.
*   `type`: Broad categorization.
*   `pinned`: Boolean. If true, the memory is immune to distillation and FAISS; it is injected perpetually into the direct LLM context payload regardless of age.
*   `is_longterm`: Boolean. Tag dictating if the block has been summarized from STM.
*   `importance`: A dynamic float calculated upon FAISS vector extraction.

## 2. FAISS Vector Math & Embedding
Synthaura Prime rejects simple keyword routing, instead employing semantic vectorization.
*   **The Model**: The system runs `sentence-transformers/all-MiniLM-L6-v2` locally on the CPU by default. Every single text block processed encodes into an array of exactly **384 dense floating-point numbers**.
*   **The Index**: Facebook AI Similarity Search (FAISS). Vectors are loaded into a physical `IndexFlatL2` structure. 
*   **Retrieval Process (`retrieve_context_for_prompt`)**: When a user inputs a query, it is encoded into a 384-dimension vector. FAISS cross-compares it across all database items utilizing an L2 (Euclidean) distance algorithm to find the absolute mathematically closest meaning. Those highly-rated blocks have their `MemoryRow.importance` scores adjusted upward and are ripped into the LLM context.

## 3. LRU Dictionary Short-Circuiting
To preserve Mac CPU cycles during intense usage, `MemoryManager._context_cache` deploys a native Python mapping dictionary.
*   `cache_key = f"{user_query}_{conversation_id}_{top_k}"`
*   If the user asks consecutive identical contextual questions, the massive PyTorch tensor logic is entirely bypassed, returning the exact data payload in `0.0ms`.
*   The array clears itself intelligently the absolute moment `MemoryManager.add_memory` is triggered to prevent stale data reading.

## 4. Proactive Background Distillation (STM -> LTM)
Large Language Models crash or heavily degrade in logic when prompt tokens overwhelm their attention windows. Synthaura mitigates this.
*   **The Trigger Check**: Inside `add_memory`, the framework evaluates all active Unpinned Short-Term Memory rows. The moment `stm_count > 6`, it engages the aggressive distillation loop.
*   **The Condenser (`ensure_within_budget`)**: 
    1. Extracts the oldest, lowest-importance STM rows.
    2. Merges their strings and passes them to the absolute fast LLM cache.
    3. Instructs the LLM: *"Summarize the core facts of these messages."*
    4. Deletes the sprawling raw STM blocks.
    5. Saves the newly generated summary into the database as a single `is_longterm=True` structural memory anchor, ensuring the AI mathematically "remembers" it forever without blowing out prompt constraints.
