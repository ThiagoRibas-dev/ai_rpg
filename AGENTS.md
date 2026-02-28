# AI-RPG Technical Architecture

This document provides a technical overview of the Solo Text AI-RPG framework, organized to guide development flow.

## Development Notes

**Planning:** Before making changes, perform an iterative planning step. Lay out a detailed implementation plan (what, where, how, why). Only execute once the plan is accepted.

**Atomic Edits:** Avoid editing whole files at once. Edit specific, targeted snippets. Be aware of replacing snippets that exist in multiple parts of a file. Keep files small (<500 lines); split if necessary.

**Code Quality:** Run `ruff check . --fix` after batches of changes. Ensure type hints are used everywhere.

**Error Handling:** Never use silent exceptions (`try/except: pass`). Always log errors with the appropriate level (`logger.error` for critical failures, `logger.warning` for degradations) and provide an informative message to help with debugging.

**Deterministic Rendering:** UI components must not "guess" how to render data. Always prioritize the `SystemManifest` (via `item_shape`) over heuristics. Use the 3-layer detection algorithm (Schema → Shape → Heuristics) to ensure accuracy.

**Magic Strings:** Never use hardcoded strings for Prefab IDs or internal field keys. Always use `PrefabID` enums and `FieldKey` constants from `app/models/vocabulary.py`.

## Core Concepts

-   **Manifest-Driven Architecture:** The game system is defined by a JSON `SystemManifest`. This defines the stats (`VAL_INT`), resources (`RES_POOL`), and mechanics. The AI does not hallucinate rules; it follows the Manifest.
-   **Prefab Protocol:** Character sheet fields are built from atomic "Prefabs". Each Prefab bundles data structure, validation logic, and UI rendering hints. UI rendering must be **Manifest-Aware**, meaning it uses manifest metadata to decide how to display complex list items (e.g., using `item_shape` to identify resource pools).
-   **Context Propagation:** Rendering logic must propagate manifest metadata (`FieldDef.config`) alongside the raw data. Avoid "pure" data components that don't know their own schema.
-   **ReAct Loop:** The game turn is an iterative **Reason + Act** loop. The AI thinks, calls atomic tools, observes results, and loops until the turn is resolved.
-   **State Invariants:** Game rules (e.g., "HP cannot exceed Max HP") are enforced by code via the `ValidationPipeline`, not by the LLM.

## System Architecture

The application is orchestrated by key components:

-   **`Orchestrator`:** The main controller. Manages the UI thread (NiceGUI), the background execution thread, and the event bridge.
-   **`ReActTurnManager`:** The "brain". Executes the game loop. It loads the active `SystemManifest`, constructs the context, and manages the chat interaction with the LLM.
-   **`ContextBuilder`:** Assembles the prompt. It generates dynamic "Cheat Sheets" based on the active Manifest, explaining valid paths (`resources.hp.current`) and tool usage to the LLM.
-   **`ToolRegistry` & `ToolExecutor`:**
    *   **Atomic Tools:** A small set of highly specific tools (`adjust`, `set`, `roll`, `mark`, `move`, `note`) handles all interactions.
    *   **Executor:** Runs the tools and triggers the **Validation Pipeline** to enforce game rules immediately after state changes.
-   **`ValidationPipeline`:** Located in `app/prefabs/validation.py`. It runs after every tool call to recalculate derived stats (formulas) and clamp values based on Prefab rules.
-   **`DBManager`:** Repository-based access to SQLite. Manages `sessions`, `game_state` (entity-component system), `manifests`, and `memories`.
-   **`VectorStore`:** ChromaDB integration for semantic search of Memories, Rules, and Turn Metadata.

## The Turn Lifecycle (ReAct Pattern)

A turn is executed by `ReActTurnManager.execute_turn` in a background thread.
*(For the full data-flow pipeline, see [Architecture](docs/01_architecture.md#turn-workflow-data-flow)).*

1.  **Context Assembly:**
    *   **Static:** System Prompt + Manifest Rules (Engine config, Dice rules).
    *   **Dynamic:** Current State (Rendered via Prefabs), Narrative History, Relevant Memories (RAG), and Active Procedure (e.g., Combat rules).

2.  **The Loop (Max 5 Iterations):**
    *   **Input:** The User's message + Current Context.
    *   **LLM Thought:** The model generates a thought process (e.g., "The player attacks. I need to roll dice and reduce goblin HP.").
    *   **Tool Call:** The model selects an atomic tool (e.g., `roll(formula="1d20+5")` or `adjust(path="resources.hp.current", delta=-5)`).
    *   **Execution & Validation:** The `ToolExecutor` runs the tool. The `ValidationPipeline` creates a "corrected" state (e.g., clamping HP to 0).
    *   **Observation:** The result is fed back to the LLM (e.g., "Rolled 18" or "HP updated to 0").

3.  **Final Narrative:**
    *   Once the AI determines the action is complete, it generates a final narrative response describing the outcome to the player.

4.  **Post-Processing:**
    *   **Suggestions:** A lightweight call generates 3-5 distinct choices for the player.
    *   **Persistence:** State, History, and Turn Metadata are saved to SQLite and Vector Store.

## Data Model

*(See [Database Schema](docs/03_database_schema.md) for full table definitions).*

-   **Manifests:** JSON definitions of game systems (D&D 5e, CoC, etc.).
-   **Game State:** A Key-Value store where every entity (Player, NPC, Location) is a JSON blob.
-   **Memories:** Stores Lore, Facts, and Events. Vector-indexed for RAG.
-   **Turn Metadata:** Stores summaries of past turns to allow the AI to "remember" long-term history via semantic search.

## Prefabs & Validation

Instead of generic JSON, data follows strict patterns defined in `app/prefabs/registry.py`:

**Logic:**
1.  **Formulas:** Defined in Manifest (`AC = 10 + dex_mod`). Calculated automatically.
2.  **Invariants:** Defined by Prefab (Current <= Max). Enforced automatically.

## Documentation Map

### Source Code
- **`app/prefabs/`**: The core logic for the "Lego Protocol" (Manifests/Validation).
- **`app/tools/handlers/`**: The atomic tool implementations.
- **`app/gui/inspectors/`**: Inspector components. Uses `RenderingMixin` for deterministic, manifest-aware rendering logic.
- **`app/gui/`**: General NiceGUI frontend components.
- **`app/setup/`**: Logic for the "Session Zero" wizard and rule extraction.

### Documentation Files
- **[Architecture](docs/01_architecture.md)**: Turn workflow, RAG service, project structure.
- **[LLM Connectors](docs/02_llm_connectors.md)**: Provider adapters and structured output strategies.
- **[Database Schema](docs/03_database_schema.md)**: Core SQL table definitions.
- **[GUI](docs/04_gui.md)**: NiceGUI layout and threading execution model.