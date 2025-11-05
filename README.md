# AI‑RPG

AI-driven, tool-using text RPG with:
- Pluggable LLM providers (Gemini and OpenAI-compatible servers, e.g., llama.cpp)
- **Prompt caching optimization** for fast, cost-efficient multi-phase turns
- Strict structured outputs + deterministic tools (dice, rules checks, state patches)
- Versioned, validated game state (SQLite) and semantic memory (ChromaDB + fastembed)
- CustomTkinter GUI with live tool log, inspectors, and world info manager

## Table of Contents
- [Features](#features)
- [Architecture at a Glance](#architecture-at-a-glance)
- [Requirements](#requirements)
- [Install](#install)
- [Configure](#configure)
- [Run](#run)
- [First-Run Walkthrough](#first-run-walkthrough)
- [How a Turn Works](#how-a-turn-works)
- [Prompt Caching & Performance](#prompt-caching--performance)
- [GUI Tour](#gui-tour)
- [Data & Storage](#data--storage)

## Features
- **Two LLM backends**: Gemini and OpenAI-compatible
- **Session Zero flow**: Define custom game mechanics via schema tools, then auto-switch to gameplay
- **Prompt caching**: Static game prompt cached across all turn phases for 16x speedup
- **Deterministic tools** with Pydantic-validated inputs (e.g., `rng.roll`, `state.apply_patch`, `character.update`)
- **Memory system**: Upsert/query/update/delete + semantic retrieval
- **World Info** (per-prompt lore) + vector search
- **Turn metadata** storage + semantic turn search
- **GUI**: Chat bubbles, tool call/result panel, state inspectors, world info manager, memory inspector, action choices

## Architecture at a Glance
- **Orchestrator**: Coordinates a three-phase turn workflow (Plan → Narrate → Choices) with shared cached context
- **Context Builder**: Separates static (cacheable) from dynamic (per-turn) content
- **Response Prefilling**: Injects dynamic context and phase instructions via assistant message prefill
- **State**: SQLite tables for sessions, game_state, memories, world_info, turn_metadata
- **Embeddings**: ChromaDB + fastembed (pluggable model via `EMBEDDING_MODEL`)
- **Tools**: Auto-discovered from `app/tools/builtin` with strict Pydantic schemas (discriminated unions)
- **GUI**: CustomTkinter app with collapsible panels and inspectors

## Requirements
- Python 3.11+
- Windows (PowerShell) is the primary dev target, but Linux/macOS should work too
- Internet access for LLMs and embedding model downloads (unless running local LLM)

## Install

### 1. Create and activate a virtual environment (Windows PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate
```

### 2. Install dependencies:
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Configure

### 1. Copy example env and edit:
```powershell
Copy-Item .exampleenv .env
```

### 2. Set environment variables in `.env`:

**LLM Provider:**
```
LLM_PROVIDER=GEMINI  # or OPENAI
```

**Gemini:**
```
GEMINI_API_KEY=your-key
GEMINI_API_MODEL=gemini-2.5-flash
```

**OpenAI-compatible (e.g., llama.cpp server):**
```
OPENAI_API_BASE_URL=http://localhost:8080/v1
OPENAI_API_KEY=sk-local-or-placeholder
OPENAI_API_MODEL=your-model-name
```

**Embeddings (fastembed):**
```
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5  # default; fast and light
```

See `.exampleenv` for more embedding model options.

## Run
```powershell
python main.py
```

## First-Run Walkthrough
1. **Launch the app** via `python main.py`
2. **Prompts panel** → Create a "Game Master" system prompt (your GM persona + style)
3. **Sessions panel** → Click "New Game"
4. **Type an action** in the input box and click "Send"
5. **Watch the turn execute:**
   - 💭 Thought bubble (planner's internal reasoning)
   - 🛠️ Tool Calls panel (tools executed and results)
   - 📖 Assistant narrative (what happens in the game)
   - 🎯 Action choice buttons (suggested next steps)
   - 📊 Inspectors update (Characters, Inventory, Quests, Memories)

## How a Turn Works

Each turn executes in **three phases**, all sharing the same **cached static prompt** for optimal performance:

### Phase 1: Planning
**Service:** `PlannerService`  
**Goal:** Decide which tools to call and why

**Prompt Structure:**
```
[Static System Instruction - CACHED]
- Game prompt (user's GM identity)
- Tool schemas
- Tool usage guidelines
- Author's note

[Chat History - Appended]
- Previous turns (user/assistant)

[Assistant Prefill - Dynamic]
- Planning phase instructions
- Current game state
- Retrieved memories
- World info
"Based on the above, here is my structured plan:"
```

**Output:** `TurnPlan` with thought process and tool calls

---

### Phase 2: Tool Execution
**Service:** `ToolExecutor`  
**Goal:** Run the planned tools and collect results

- Executes each tool call with type-based dispatch
- Validates arguments against Pydantic schemas
- Updates UI with tool call/result events
- Tracks memory tool usage for inspector refresh

---

### Phase 3: Narrative
**Service:** `NarratorService`  
**Goal:** Write what happens based on planning + tool results

**Prompt Structure:**
```
[Static System Instruction - CACHED ✅]
- Same cached prompt as Planning phase!

[Chat History - Appended]
- Same history (no updates yet)

[Assistant Prefill - Dynamic]
- "[Planning Phase] My plan was: ..."
- "[Tool Results] What happened: ..."
- Narrative phase instructions
- Current game state (post-tools)
- Retrieved memories
"Here's what happens:"
```

**Output:** `NarrativeStep` with:
- Second-person narrative ("You...")
- Turn metadata (summary, tags, importance)
- Proposed patches (if inconsistencies detected)
- Memory intents (optional)

---

### Phase 4: Action Choices
**Service:** `ChoicesService`  
**Goal:** Suggest 3-5 next actions for the player

**Prompt Structure:**
```
[Static System Instruction - CACHED ✅]
- Same cached prompt again!

[Chat History - Appended]
- Still same history

[Assistant Prefill - Dynamic]
- "[Narrative Phase] I just wrote: ..."
- Choice generation instructions
"Here are the action choices:"
```

**Output:** `ActionChoices` with 3-5 short, actionable options

---

### Phase 5: Finalization
- Apply any patches from the narrative
- Apply memory intents
- **Add narrative to chat history** (now all phases complete)
- Persist session to database
- Refresh UI inspectors

## Prompt Caching & Performance

### How It Works
The system separates prompt content into two categories:

**Static (Cached):**
- User's game prompt
- Tool schemas
- Tool usage guidelines
- Author's note

This content is sent once and **cached by the LLM API**, then reused across all three phases (Planning, Narrative, Choices) in the same turn, and across subsequent turns.

**Dynamic (Appended via Prefill):**
- Phase-specific instructions
- Current game state
- Retrieved memories
- World info
- Prior phase outputs (plan → narrative → choices)

This content changes every phase/turn and is injected via **assistant message prefill** (response suffixing).

### Benefits
- **~16x speedup** in prompt processing (only dynamic content processed)
- **~16x cost reduction** on APIs that charge for input tokens
- **Consistent context** across all phases (no prompt variation)

### Cache Invalidation
The cache is rebuilt only when:
- Game mode changes (SETUP → GAMEPLAY)
- Author's note is edited
- Tool availability changes

Otherwise, the same static instruction is reused indefinitely.

### First-Person Phase Prompts
Because we use assistant prefill, phase instructions are written from the AI's perspective:

```
# PLANNING PHASE
I am now in the planning phase. My role is to...
```

Instead of traditional second-person instructions:
```
Your goal is to select appropriate tools...
```

This creates a natural "AI talking to itself" flow that works well with prefill.

## GUI Tour

### Left Panel: Chat Window
- **User messages** (blue, right-aligned)
- **AI messages** (green, left-aligned)
- **System messages** (gray, left-aligned)
- **Thought bubbles** (gold border, center) - AI's internal planning

### Right Panel: Control & Inspectors

#### Prompt Management
- Create/edit/delete game master prompts
- Click to select active prompt

#### Game Sessions
- Create new game sessions
- Load existing sessions
- Session name and game time displayed in header

#### Advanced Context
- **Memory field**: Persistent notes for the AI
- **Author's Note**: Style/tone instructions
- **World Info Manager**: Add lore snippets (per-prompt)

#### Game State Inspector (Tabs)
1. **Characters**: Live character data (HP, stats, conditions, custom properties)
2. **Inventory**: Items, currency, capacity; quick actions
3. **Quests**: Active quests with progress tracking
4. **Memories**: Browse/filter/search; create/edit/delete; import/export
5. **Tool Calls**: Real-time log of every tool execution
6. **State Viewer**: Raw JSON state viewer (debug tool)

### Action Choices
- Appear below the chat after AI narrates
- Click to auto-fill input and send

## Data & Storage

### SQLite Database: `ai_rpg.db`
- `sessions` - Game sessions with mode tracking (SETUP/GAMEPLAY)
- `game_state` - Versioned entity storage (characters, inventory, quests, etc.)
- `memories` - Memory entries with kind, priority, tags, fictional time
- `world_info` - Lore snippets linked to prompts
- `turn_metadata` - Turn summaries with importance ratings
- `schema_extensions` - Custom property definitions (Session Zero)

### Vector Store: `./chroma_db`
- **Turn embeddings** - Semantic search of past turns by importance
- **Memory embeddings** - Semantic retrieval for context
- **World info embeddings** - Lazy-indexed lore retrieval

### Embedding Model
Configured via `EMBEDDING_MODEL` environment variable. Default: `BAAI/bge-small-en-v1.5` (384 dims, ~50MB, fast).

See `.exampleenv` for other options (better accuracy vs. speed trade-offs).

---

**License:** AGPLv3