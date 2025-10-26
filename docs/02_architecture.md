# Architecture

This document outlines the system architecture, data flow, and core components of the AI-RPG project.

## System Architecture
- GUI renders streamed tokens and inline tool events.
- Orchestrator executes a per-turn pipeline: Plan → Tools → Narrative → Patches/Memories.
- Provider adapters normalize Gemini and OpenAI-compatible APIs.
- Tools are deterministic functions with JSON schemas + Python handlers.
- Optional RAG for flavor and continuity.

## Turn Workflow (Data Flow)

The system uses a fast path vs. full pipeline approach to minimize latency.

**1) Preprocess**
- Detect slash-commands or equivalent input via a menu (/roll 1d20, /inventory) handled locally.
- Language detect, short-circuit trivial echo/state reads.

**2) Retrieve context**
- Short-term transcript window (N recent turns)
- RAG prefetch: last user input → embeddings search (non-blocking, with timeout ~150–300 ms)
- State snapshot: only relevant entities requested via selectors (scene, party, location)

**3) Tool Provisioning & Planning (Schema: `TurnPlan`)**
- The `Orchestrator` queries the `ToolRegistry` for all available tool schemas.
- These schemas are sent to the LLM along with the prompt and the `TurnPlan` schema.
- The LLM's response is constrained to the `TurnPlan` schema, forcing it to provide a structured plan (e.g., `{"thought": "...", "tool_calls": [...]}`). This avoids unreliable text parsing.

**4) Tool Execution & Result Consolidation**
- The `Orchestrator` receives the `tool_calls` request.
- It parses the request, validates the arguments against the tool's JSON schema, and executes the corresponding Python handler via the `ToolRegistry`.
- The result of the tool execution (e.g., `15`) is captured.

**5) Narrative Generation (Schema: `NarrativeStep`)**
- The `Orchestrator` makes a second call to the LLM, providing the tool results and the `NarrativeStep` schema.
- The LLM's response is constrained to the `NarrativeStep` schema, forcing it to provide the narrative, `StatePatch` proposals, and `MemoryIntent` proposals in a structured format.
- The `Orchestrator` can then reliably extract and process each part of the response.

**6) Validation and commit**
- Engine validates ops; if safe, commit and display “State updated”
- Memory dedupe/scoring; low-priority memories can be queued for batch

**7) Finalization**
- Save messages, tool events, patches; compute token/latency; emit telemetry

## RAG Service
- Local vector index (FAISS/sqlite-vss).
- Index lore bible + episodic summaries + player prefs.
- Query with filters; timebox ≤200 ms.

## Project structure
- app/gui: tkinter views
- app/core: orchestrator and prompts
- app/llm: provider adapters
- app/tools: deterministic tools and registry
- app/io: Pydantic schemas (single source of truth)
- app/database: SQLite helpers
- docs: design and operations
