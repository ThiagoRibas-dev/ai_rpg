# AI-RPG Technical Architecture

This document provides a technical overview of the AI-RPG engine, intended for developers.

## Development Notes

**Planning:** Before making any changes, we will perform an iterative planning step, laying out a detailed step-by-step implementation plan (what, where, how, why). Only once the plan has been accepted, we will execute the plan and edit the files in question.

**Editing Files:** Avoid trying to edit whole files at once if possible. Edit specific, directed, targeted snippets at a time, always planning the whole chain of edits beforehand. Be aware of replacing snippets that exist in multiple parts of a given file. Files should be kept as relatively small. If a file is becoming too large (500+ lines) then split the file into two or more.

**Ruff Linter:** During Execution, after performing a batch of changes, always run `ruff check . --fix` to ensure things are in order.

**Logging:** All code will contain tracking logs that output to the console so that errors are easier to debug.

## Core Concepts

-   **Modularity:** The system is divided into distinct services, each with a clear responsibility (e.g., planning, narration, database management, UI handling).
-   **State Separation:** Game state is explicitly managed and stored. The LLM is stateless; it reads state via tools and proposes changes, but does not hold state itself.
-   **Type-Safety and Predictability:** Pydantic models are used extensively to define schemas for LLM outputs and tool inputs. This ensures that data is structured and validated at every step, reducing unpredictable behavior.
-   **Optimized LLM Interaction:** The system is designed to minimize token usage and latency by leveraging API-side context caching through careful prompt engineering.

## System Architecture

The application is orchestrated by a few key components:

-   **`Orchestrator`:** The main application controller. It initializes all components and manages the main UI loop. It launches background threads for turn execution.
-   **`TurnManager`:** The "brain" of the operation. It contains the logic for a single game turn, coordinating the sequence of calls to various services (Planner, Executor, Narrator, Choices).
-   **`ContextBuilder`:** Responsible for assembling the prompts sent to the LLM. It separates the prompt into a static, cacheable `system_instruction` and a dynamic, per-turn context.
-   **`LLMConnector`:** An abstract base class defining the interface for LLM interactions. Concrete implementations (`GeminiConnector`, `OpenAIConnector`) handle the specifics of each API.
-   **`DBManager`:** Manages the connection to the SQLite database and provides a repository-based interface for all data operations.
-   **`VectorStore`:** Manages the ChromaDB instance and provides an interface for embedding and searching text for semantic retrieval.
-   **`ToolRegistry` & `ToolExecutor`:** The `Registry` auto-discovers and validates tools from Pydantic schemas. The `Executor` runs the tools requested by the LLM.

## The Turn Lifecycle (In-Depth)

A single turn, managed by `TurnManager.execute_turn`, is a sequence of LLM calls and local processing. All LLM calls in this sequence share the same static `system_instruction` to maximize caching benefits.

1.  **Context Assembly (`ContextBuilder`):**
    *   `build_static_system_instruction()` is called. If the author's note or game mode hasn't changed, this content is identical to the previous turn's, allowing the LLM API to cache it.
    *   `build_dynamic_context()` is called to gather the current state, relevant memories, and world info for this specific turn.

2.  **Plan Generation (`PlannerService.create_plan`):**
    *   **1st LLM Call (JSON Mode).**
    *   **Input:** Static instruction, chat history, and dynamic context.
    *   **Output:** A `TurnPlan` Pydantic model containing the AI's analysis and a list of `plan_steps`.

3.  **Iterative Tool Selection (`PlannerService.select_tools_for_step`):**
    *   **2nd to Nth LLM Calls (Tool Calling Mode).**
    *   The system loops through each `plan_step` from the `TurnPlan`.
    *   For *each step*, a small, focused LLM call is made, asking the AI to select the appropriate tool(s) for just that single step.
    *   **Rationale:** This iterative approach is more reliable than a single large tool-calling request, as it prevents the LLM from failing to select tools for later steps in a complex plan.

4.  **Tool Execution (`ToolExecutor.execute`):**
    *   **No LLM Calls.**
    *   The list of tool calls gathered from the previous phase is executed locally. Results are collected.

5.  **Narration (`NarratorService.write_step`):**
    *   **(N+1)th LLM Call (JSON Mode).**
    *   **Input:** The same static instruction, history, the original plan, and the results from tool execution.
    *   **Output:** A `ResponseStep` Pydantic model containing the narrative text, proposed state patches, memory intents, and turn metadata.

6.  **Choice Generation (`ChoicesService.generate`):**
    *   **(N+2)th LLM Call (JSON Mode).**
    *   **Input:** The same static instruction, history, and the newly generated narrative from the previous phase.
    *   **Output:** An `ActionChoices` Pydantic model containing a list of suggested player actions.

7.  **State Finalization:**
    *   Proposed patches and memory intents from the `ResponseStep` are applied.
    *   The final narrative is added to the session's chat history.
    *   The session state is persisted to the database.

## LLM Interaction Patterns

The engine employs two key strategies for interacting with the LLM.

### Prompt Engineering for API-Side Caching

The application is explicitly designed to leverage the context caching of LLM providers. It does this by splitting every prompt into two parts:

-   **`system_instruction`:** A large, static block of text containing the AI's core persona, instructions, and all available tool schemas. This is passed as the `system_prompt` (or equivalent) to the API. Since this text rarely changes, the API can cache its processed representation.
-   **Assistant Prefill:** The dynamic, per-turn context (current state, memories, phase-specific instructions) is appended to the chat history as the start of an assistant's response. The LLM's task is then to "complete" this response.

This ensures that only the small, dynamic portion of the prompt requires full processing on each call, dramatically improving performance. This is also why the phase templates are written in the first person (e.g., "I am now in the planning phase..."), as they form the beginning of the AI's own "thought process."

### Hybrid Output Strategy: JSON Mode & Tool Calling

The engine uses both of the primary LLM output modes, choosing the best one for each task:

1.  **JSON Schema Mode (Structured Output):**
    *   **When:** Used for complex, nested data structures like the `TurnPlan` and `ResponseStep`.
    *   **Why:** It is highly reliable for forcing the LLM to generate a complete, deeply structured JSON object that can be validated against a Pydantic model. This is critical for the planning and narration phases where multiple distinct pieces of information are required.

2.  **Native Tool/Function Calling Mode:**
    *   **When:** Used exclusively in the `PlannerService.select_tools_for_step` phase.
    *   **Why:** This mode is optimized for the specific task of selecting one or more functions from a predefined list and generating their arguments. It is more robust and natural for this use case than trying to force the LLM to write the tool calls as part of a larger JSON blob.

This hybrid approach uses the strengths of each LLM feature for maximum reliability.

## Data Model

-   **SQLite:** The primary store for structured, relational data. The schema is defined in `db_manager.py` and uses a repository pattern for data access. Key tables include `sessions`, `game_state` (a versioned key-value store for entities), and `memories`.
-   **ChromaDB:** A vector database used for semantic search. Collections are maintained for `memories`, `world_info`, and `turn_metadata` to enable relevance-based retrieval of unstructured text.

## Tool System

-   **Auto-Discovery:** The `ToolRegistry` automatically scans the `app/tools/builtin` directory. Any Python file with a `handler` function is a candidate.
-   **Schema-Driven:** A tool is only registered if its module name (e.g., `memory_upsert.py`) corresponds to a tool name defined in a Pydantic schema in `app/tools/schemas.py` (e.g., `name: Literal["memory.upsert"]`).
-   **Type-Safe Execution:** The `ToolExecutor` uses the Pydantic model *type* as the key for dispatch. This avoids string matching and ensures that the handler receives a fully validated Pydantic model as input, preventing a large class of runtime errors.

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
- **[V9 TODO](docs/todos/v9_TODO.md)**
- **[V10 TODO](docs/todos/v10_TODO.md)**
- **[V11 TODO](docs/todos/v11_TODO.md)**
- **[V12 TODO](docs/todos/v12_TODO.md)**
- **[V13 TODO](docs/todos/v13_TODO.md)**
