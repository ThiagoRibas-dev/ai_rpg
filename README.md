# AI‑RPG

AI-driven, tool-using text RPG with:
- Pluggable LLM providers (Gemini and OpenAI-compatible servers, e.g., llama.cpp)
- Strict structured outputs + deterministic tools (dice, rules checks, state patches)
- Versioned, validated game state (SQLite) and semantic memory (ChromaDB + fastembed)
- CustomTkinter GUI with live tool log, inspectors, and world info manager

Table of Contents
- Features
- Architecture at a Glance
- Requirements
- Install
- Configure
- Run
- First-Run Walkthrough
- How a Turn Works
- GUI Tour
- Data & Storage
- Available Tools
- Troubleshooting
- Tests
- Project Structure
- Roadmap
- Contributing

Features
- Two LLM backends: Gemini and OpenAI-compatible
- Session Zero flow: define custom game mechanics via schema tools, then auto-switch to gameplay
- Deterministic tools with Pydantic-validated inputs (e.g., rng.roll, state.apply_patch, character.update)
- Memory system: upsert/query/update/delete + semantic retrieval
- World Info (per-prompt lore) + vector search
- Turn metadata storage + semantic turn search
- GUI: Chat bubbles, tool call/result panel, state inspectors, world info manager, memory inspector, action choices

Architecture at a Glance
- Orchestrator: Plans → executes tools → audits → narrates → writes metadata → suggests actions
- State: SQLite tables for sessions, game_state, memories, world_info, turn_metadata
- Embeddings: ChromaDB + fastembed (pluggable model via EMBEDDING_MODEL)
- Tools: Auto-discovered from app/tools/builtin with strict Pydantic schemas (discriminated unions)
- GUI: CustomTkinter app with collapsible panels and inspectors

Requirements
- Python 3.11+
- Windows (PowerShell) is the primary dev target, but Linux/macOS should work too
- Internet access for LLMs and embedding model downloads (unless running local LLM)

Install
- Create and activate a virtual environment (Windows PowerShell):
  - python -m venv .venv
  - .\.venv\Scripts\Activate
- Install dependencies:
  - python -m pip install --upgrade pip
  - pip install -r requirements.txt

Configure
- Copy example env and edit:
  - PowerShell: Copy-Item .exampleenv .env
- Set environment variables in .env:
  - LLM_PROVIDER=GEMINI or OPENAI

Gemini
- GEMINI_API_KEY=your-key
- GEMINI_API_MODEL=gemini-2.5-flash (or similar)

OpenAI-compatible (e.g., llama.cpp server)
- OPENAI_API_BASE_URL=http://localhost:8080/v1
- OPENAI_API_KEY=sk-local-or-placeholder
- OPENAI_API_MODEL=your-model-name

Embeddings (fastembed)
- EMBEDDING_MODEL=BAAI/bge-small-en-v1.5 (default; fast and light)

Run
- python main.py

First-Run Walkthrough
1) Launch the app.
2) Prompts panel → create a “Game Master” system prompt (your GM persona + style).
3) Sessions panel → New Game.
4) Type an action in the input box and click Send.
5) Watch:
   - Thought bubble (planner intent)
   - Tool Calls panel (tools executed and results)
   - Assistant narrative and suggested action buttons
   - Inspectors update (Characters, Inventory, Quests, Memories)

How a Turn Works
- Plan: PlannerService generates a TurnPlan (strictly typed against available tool models).
- Execute: ToolExecutor runs tool calls (with UI logging).
- Audit: Optional consistency check; may apply patches/memory updates.
- Narrate: LLM writes the next scene + turn metadata (summary, tags, importance).
- Choices: LLM suggests 3–5 concise next actions for the player.

GUI Tour
- Chat (left): User/AI/system bubbles + “AI Thinking” thoughts.
- Tool Calls tab: Every tool invocation + result (success/error).
- Inspectors (right):
  - Characters: live character data (attributes, conditions, properties).
  - Inventory: items, currency, capacity; quick “drop item” helper.
  - Quests: active quests with progress/objectives.
  - Memories: browse, filter, search; create/edit/delete; import/export.
  - State Viewer: view/refresh raw state JSON; copy; clear all (debug).
- Advanced Context:
  - Memory and Author’s Note fields persist per session.
  - World Info Manager to add/edit lore snippets per prompt.

Data & Storage
- SQLite DB: ai_rpg.db
  - sessions, game_state, memories, world_info, turn_metadata, schema_extensions
- Vector store: ./chroma_db (ChromaDB persistent store)
- Turn metadata embeddings: semantic search of prior turns
- Memory embeddings: semantic search for planning/context

Available Tools (high level)
- rng.roll: “2d6+1” style dice
- math.eval: safe arithmetic evaluation
- time.now / time.advance: timestamps and fictional time updates
- state.query / state.apply_patch: read/write structured state
- character.update: validated updates (core + custom properties) with game-logic hooks
- memory.upsert / memory.query / memory.update / memory.delete
- rag.search: stubbed lore chunks (example)
- rules.resolve_action: compute final formula/DC with LLM-provided policy

Troubleshooting
- LLM credentials:
  - “GEMINI_API_KEY not set” or “OPENAI_API_* not set” → check .env
- Embedding model download fails:
  - Ensure internet access, or set a different EMBEDDING_MODEL
  - Windows CPU: requirements include onnxruntime-directml; adjust to onnxruntime if needed
- Blank UI or tool logs don’t update:
  - Check terminal logs; UI uses a queue and polls every 100ms
- Vector store corruption:
  - Delete ./chroma_db (will rebuild) if testing and you want a clean slate

Tests
- Install pytest: pip install pytest
- Run core tests:
  - pytest tests/test_character_update.py
- Ad-hoc state test:
  - python test_state.py

Project Structure
- app/core: Orchestrator, LLM services, context building, vector store
- app/gui: CustomTkinter UI (main view, inspectors, world info manager, styles)
- app/tools: Pydantic tool schemas + builtin tool handlers (auto-discovered)
- app/models: Typed entities, sessions, memory, prompts, etc.
- app/database: DBManager (SQLite schema + CRUD)
- docs: Architecture, connectors, GUI, roadmap (if present)
- chroma_db: ChromaDB persistent store

Roadmap
- See docs/roadmap.md for planned milestones (v1–v6), including:
  - Session Zero, advanced context, memory, RAG, schema-aware mechanics, polish
