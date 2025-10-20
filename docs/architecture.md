# System Architecture

- **GUI (customtkinter)**
  - Renders streamed tokens and tool events
  - Dispatches user input to Orchestrator
  - Non-blocking via background worker threads/async
- **Orchestrator (brain)**
  - Builds prompts, enforces schemas, runs the per-turn workflow (plan → retrieve → tool calls → patch → respond)
  - Validates LLM JSON outputs; retries or falls back on parse errors
  - Applies latency policy (fast path/full pipeline)
- **Provider Abstraction Layer**
  - GeminiAdapter, OpenAIAdapter, LlamaCppAdapter (OpenAI-compatible)
  - Streaming, tool/JSON-schema compatibility shims, retries/rate-limits
- **Tool Registry**
  - Deterministic tools: rng.roll, math.eval, time.now, memory.upsert, state.apply_patch, rag.search, asset.resolve
  - Each tool has a JSON Schema and a Python handler
- **State Manager**
  - SQLite store with JSON columns; Pydantic models; JSON Patch commit/rollback
  - Memory types: episodic, semantic, long-term, world lore, user preferences
  - LLM proposes MemoryIntent/StatePatch; validators dedupe and enforce constraints
- **RAG Service**
  - Local vector index (FAISS/SQLite-VSS) + metadata/tagged filters
  - Incremental indexers; supports offline/open-source or provider embeddings
- **Telemetry/Logging**
  - Structured logs of turns, provider usage, token counts, latency; redaction for privacy
- **Config/Secrets**
  - Per-provider keys; per-session overrides;

## Folder Structure

- `app/`
  - `gui/` (customtkinter views, view-models)
  - `core/` (orchestrator.py, prompts.py, policies.py)
  - `providers/` (gemini.py, openai_compat.py, llama_cpp.py)
  - `tools/` (registry.py, builtin/*.py)
  - `state/` (models.py, store.py, patches.py)
  - `rag/` (index.py, embed.py, search.py)
  - `io/` (schemas.py, validation.py, streaming.py)
  - `telemetry/` (log.py, metrics.py, tracing.py)
  - `config.py`