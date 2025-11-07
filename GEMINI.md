## High-Level Specification

An advanced, text-based RPG engine powered by Large Language Models (LLMs). The engine dynamically generates narrative, manages game state, and responds to player actions by intelligently retrieving and managing context. The core design focuses on:

- **Modular architecture** separating state management, decision logic, and LLM interaction
- **Multi-backend support** for LLMs (Gemini, OpenAI-compatible APIs)
- **Prompt caching optimization** using static/dynamic content separation and response prefilling
- **Three-phase turn workflow** (Planning → Narrative → Choices) sharing a cached system prompt
- **Type-safe tool execution** with Pydantic discriminated unions
- **Semantic memory and turn search** via ChromaDB vector store

### Turn Workflow Optimization

Each turn executes three phases that **share the same cached static prompt**:

#### Static System Instruction (Cached)
Rebuilt only when game mode changes or author's note is edited:
- User's game prompt (identity/style)
- Tool schemas (available tools JSON)
- Tool usage guidelines
- Author's note (style instructions)

#### Dynamic Context (Injected via Prefill)
Changes every turn and is appended via **assistant message prefill**:
- Phase-specific instructions (planning/narrative/choices)
- Current game state (queried from database)
- Retrieved memories (semantic + keyword search)
- World info (contextual lore)
- Prior phase outputs (plan thought → tool results → narrative)

#### Benefits
- **Speedup** on prompt processing (only dynamic content processed)
- **Cost reduction** on token-charged APIs
- **Partial cache breaks** between phases (same static instruction)
- **Consistent context** across all phases

#### Implementation Details
1. **Session.system_prompt**: Stored separately from chat history (not in messages array)
2. **ContextBuilder.build_static_system_instruction()**: Builds cacheable prompt once per session/mode
3. **ContextBuilder.build_dynamic_context()**: Builds fresh context every turn
4. **Services use assistant prefill**: Each phase injects instructions + context as assistant message
5. **Chat history updated once**: After all phases complete, narrative is added to history

### First-Person Phase Prompts

Because we use assistant message prefill (the AI "continues" from a partial message), phase instructions are written from the AI's perspective:

**Planning Phase:**
```
I am now in the planning phase. My role is to:
- Analyze the player's action for feasibility...
```

**Narrative Phase:**
```
[Planning Phase - My Internal Reasoning]
{plan.thought}

[Tool Execution - What Actually Happened]
{tool_results}

I am now in the narrative phase. My role is to:
- Write the scene based on my planning intent...
```

**Choices Phase:**
```
[Narrative Phase - What I Just Wrote]
{narrative.narrative}

I am now generating 3-5 action choices for the player...
```

This creates a natural "AI talking to itself about what it needs to do" flow.

## Detailed Specification & Documentation

This project is documented across several files to keep the information organized and easy to navigate.

- **[Introduction](docs/01_introduction.md)**
- **[System Architecture](docs/02_architecture.md)**
- **[LLM Connectors](docs/03_llm_connectors.md)**
- **[Database Schema](docs/04_database_schema.md)**
- **[GUI](docs/05_gui.md)**
- **[Roadmap](docs/roadmap.md)**

## Project TODOs

- **[V0 TODO](docs/todos/v0_TODO.md)**
- **[V1 TODO](docs/todos/v1_TODO.md)**
- **[V1.5 TODO](docs/todos/v1.5_TODO.md)**
- **[V1.6 TODO](docs/todos/v1.6_TODO.md)**
- **[V1.7 TODO](docs/todos/v1.7_TODO.md)**
- **[V2 TODO](docs/todos/v2_TODO.md)**
- **[V3 TODO](docs/todos/v3_TODO.md)**
- **[V4 TODO](docs/todos/v4_TODO.md)**
- **[V5 TODO](docs/todos/v5_TODO.md)**
- **[V6 TODO](docs/todos/v6_TODO.md)**
- **[V7 TODO](docs/todos/v7_TODO.md)**
- **[V8 TODO](docs/todos/v8_TODO.md)**

## Notes

**Planning:** Before making any changes, we will perform an iterative planning step, laying out a detailed step-by-step implementation plan (what, where, how, why). Only once the plan has been accepted, we will execute the plan and edit the files in question.

**Editing Files:** Avoid trying to edit whole files at once if possible. Edit specific, directed, targeted snippets at a time, always planning the whole chain of edits beforehand. Be aware of replacing snippets that exist in multiple parts of a given file. Files should be kept as relatively small. If a file is becoming too large (500+ lines) then split the file into two or more.

**Ruff Linter:** During Execution, after performing a batch of changes, always run `ruff check . --fix` to ensure things are in order.

**Logging:** All code will contain tracking logs that output to the console so that errors are easier to debug.

**Prompt Caching:** When implementing new features, consider whether new prompt content should be static (cached) or dynamic (per-turn). Static content should go in `build_static_system_instruction()`, dynamic content in `build_dynamic_context()` or phase-specific prefills.
