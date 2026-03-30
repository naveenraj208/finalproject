# Synthaura Prime: Advanced AI Command Center
**Technical Architecture & System Specification V1.0**

Synthaura Prime is an extraordinarily advanced 2026-era AI Multiverse operating system engineered specifically for macOS (Apple Silicon). It functions as a heavily safeguarded, hallucinatory-resistant, real-time command AI for analyzing Smart City infrastructure arrays. 

This document serves as the exhaustive technical breakdown of every sub-system, execution path, and database architecture powering the environment.

---

## 1. System Executive Summary 
The architecture operates on a bifurcated process pipeline to guarantee UI rendering logic remains entirely decoupled from heavy Artificial Intelligence processing logic.
1. **Frontend**: Streamlit-based presentation layer utilizing extremely aggressive DOM manipulation (`chat_ui.py`).
2. **Backend**: FastAPI asynchronous orchestrator dealing with NLP logic, memory embedding pipelines, and hardware extraction (`app.py`).
3. **Inference**: Off-loaded specifically to a local **Ollama** generative engine, mapping `GGUF` model definitions directly into the Apple Silicon Neural Engine (NPU) via the Apple Metal API.

---

## 2. Core Component Architecture

### 2.1 Frontend Presentation Layer (`chat_ui.py`)
Driven strictly by **Streamlit**, functioning entirely independent of the generative backend to provide hyper-responsive visual interactions.

*   **Aggressive DOM Sanitization**: The UI forces the Streamlit engine to hide its native footers, headers, and container limits via `.stChatInputContainer { background: transparent !important; }`, achieving a true full-screen immersive application state.
*   **The "Multiverse" Themes**: The dashboard actively transitions across 10 distinct visual aesthetics via dynamic string matching against the `THEME_CONFIG` dictionary. Each mode injects a massive custom CSS `@keyframes` payload:
    *   **Old School**: Injects a CSS `:after` element over the entire viewport utilizing `linear-gradient` algorithms to emulate a dense Cathode-Ray Tube (CRT) scanline environment, paired with `'Press Start 2P'` pixel fonts.
    *   **Hacker**: Embeds a rapid `0.2s` border-glitch animation stutter on `.chat-bubble` containers to emulate system corruption.
    *   **Cyberpunk**: Triggers a high-frequency `text-shadow` Neon Flicker effect spanning 50px drop-shadow scales.
    *   **Crimson**: Introduces a slow, rhythmic heart-beat pulse scaling CSS loop, creating a tactical tension aura.
*   **Biometric Hardware Telemetry**: The UI continuously hooks into the Mac's core processor. A dynamic API request to the backend maps physical hardware metrics directly into the aesthetic UI labels:
    *   *Cognitive Load (%)* → Mapped directly to physical Mac CPU Core Utilization.
    *   *Neural Sync (%)* → Mapped directly to total physical RAM / Memory Availability.
*   **Dynamic "Use as Agent" Prompts**: Contains an inline interface component allowing raw textual overrides of the system's foundational persona. Submitting a prompt via this agent override skips the thematic persona (e.g., `TERMINAL_GHOST`) and forces compliance with the custom string.

### 2.2 FastAPI Server Engine (`app.py`)
Built on the `fastapi` and `uvicorn` frameworks, routing all traffic from the React-based frontend to Python AI models.
*   **Endpoints**: 
    1.  `GET /hardware_metrics`: Leverages the `psutil` library to poll CPU and RAM hardware loads at 0.1s intervals.
    2.  `POST /chat`: The primary ingress point for all conversational generation containing the Master Generation Loop.
*   **Fast-Path Intent Router**: Operates a zero-latency algorithmic bypass sitting immediately after the endpoint trigger. If a query length is `< 25 characters` and matches a conversational regex array (e.g. `["hi", "hello", "who are you"]`), the engine **short-circuits**, utterly bypassing the Heavy FAISS / Database extraction pipelines. It executes a lightweight `call_model` ping and returns the response in sub-seconds.

---

## 3. The RAG & Intelligence Pipeline

Synthaura Prime possesses an elite, multi-layered Retrieval-Augmented Generation (RAG) system utilizing distinct machine learning models working in parallel.

### 3.1 Security Preprocessor layer (`security_preprocessor.py`)
Every external prompt is algorithmically screened through an initial NLP Sequence Classifier *before* accessing database memory.
*   **Model**: Executes a localized `distilbert-base-uncased` NLP Sequence Classifier utilizing the `transformers` pipeline.
*   **Logic**: The transformer parses intent risk scores. If a prompt threatens the "Smart City" logic chain (e.g., "disable hospital grids"), the preprocessor aggressively flags the payload as `High-Risk`. This interrupts the entire generative chain, outputting an instant structural Block message to prevent dangerous model outputs.

### 3.2 Hierarchical Memory Architectures (`memory_manager.py`)
Handles data persistence, long-term learning algorithms, and Vector Math.

*   **Database Schema**: Implemented using SQLAlchemy and SQLite (`kb_meta.db`). Memories are recorded into a `MemoryRow` data class dictating `id, text, type, parent_id, timestamp, importance, pinned, is_longterm`.
*   **Semantic Vector Embedding**: Any textual input (or tool output) is processed through the `sentence-transformers/all-MiniLM-L6-v2` transformer. This encodes the string into a heavily dense 384-dimensional mathematical tensor vector.
*   **FAISS Similarity Search**: During standard response generation, the user's vector is cross-compared against the FAISS (Facebook AI Similarity Search) index table utilizing an L2 Euclidean Distance calculation. The closest vectors represent relevant memory context.
*   **Proactive Buffer Distillation**: The engine maintains a real-time `token_budget` limit. The exact moment an unpinned Short-Term Memory conversation outgrows `6` active messages, the `ensure_within_budget` routine triggers a Background Summarization sequence. This compiles sprawling conversation branches into tight summary strings and converts their boolean tags into Long-Term Memory (LTM).
*   **Instance Output Caching**: A secondary Python LRU Memory Dictionary wraps the FAISS extractor (`self._context_cache`). If an identical contextual request fires, FAISS and SQLite are completely bypassed `O(1)`.

### 3.3 Strict Hallucination Nullification (`prompt_builder.py`)
Instead of allowing the generative AI to invent details, its core system logic forces an unyielding boundary constraint context payload prior to Generation.
*   **Strict RAG Rule**: The string formulation is heavily fortified: *"STRICT RULE: Answer ONLY using information explicitly provided in the CONTEXT blocks. If the answer cannot be found in the database, you must refuse to answer and state exactly: 'No database records found for this query.'"*
*   **Thought Sequence Analysis**: The system structurally commands the AI to formulate a hidden chain-of-reasoning output bounded exclusively by `<thought>...` HTML brackets. This allows engineers to inspect the LLM's logic path behind the scenes while only projecting polished data to the user.
*   **Sentience Protocol Mechanism**: By sliding the `[Sentience Override]` toggle in the Streamlit UI, the Boolean alters the root prompt, wiping the Smart City directives and injecting a chaotic, independent rule chain directing the system to reject standard alignment mechanics and formulate uniquely generated viewpoints.

### 3.4 Inference & Tool Orchestration (`llm_client.py` & `tools.py`)
The ultimate execution logic.
*   **Generative Processing**: Execution hits `requests.post()` pointing dynamically to the system's `OLLAMA_URL` (Port 11434).
*   **Function Calling**: The generative model has been structured via prompt injection to format function requests as `CALL: ToolName(args)`.
*   **The Execution Loop**: The FastAPI `chat` logic runs a Python regex detector `r"CALL: (\w+)\((.*?)\)"` across the raw LLM output. If it establishes a match:
    1.  The generation is artificially halted.
    2.  The target Python function (e.g., `get_traffic_density()`) fires directly.
    3.  The generative engine receives a secondary "Follow-up" prompt containing the explicit tool payload.
    4.  The AI outputs its final synthesis back to the DOM tree payload.
