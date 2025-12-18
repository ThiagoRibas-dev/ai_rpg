# AI-RPG Technical Architecture

This document provides a technical overview of the Solo Text AI-RPG framework, organized to guide development flow.

## Development Notes

**Planning:** Before making changes, perform an iterative planning step. Lay out a detailed implementation plan (what, where, how, why). Only execute once the plan is accepted.

**Atomic Edits:** Avoid editing whole files at once. Edit specific, targeted snippets. Be aware of replacing snippets that exist in multiple parts of a file. Keep files small (<500 lines); split if necessary.

**Code Quality:** Run `ruff check . --fix` after batches of changes. Ensure type hints are used everywhere.

## Core Concepts

-   **Manifest-Driven Architecture:** The game system is defined by a JSON `SystemManifest`. This defines the stats (`VAL_INT`), resources (`RES_POOL`), and mechanics. The AI does not hallucinate rules; it follows the Manifest.
-   **Prefab Protocol:** Character sheet fields are built from atomic "Prefabs" (e.g., `RES_TRACK` for stress boxes, `VAL_STEP_DIE` for polyhedral dice). Each Prefab bundles data structure, validation logic, and UI rendering hints.
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

-   **Manifests (`manifests` table):** JSON definitions of game systems (D&D 5e, CoC, etc.).
-   **Game State (`game_state` table):** A Key-Value store where every entity (Player, NPC, Location) is a JSON blob.
-   **Memories (`memories` table):** Stores Lore, Facts, and Events. Vector-indexed for RAG.
-   **Turn Metadata:** Stores summaries of past turns to allow the AI to "remember" long-term history via semantic search.

## Prefabs & Validation

Instead of generic JSON, data follows strict patterns defined in `app/prefabs/`:

| Prefab ID | Data Shape | Usage |
|:---|:---|:---|
| `VAL_INT` | `int` | Attributes (Str: 18) |
| `RES_POOL` | `{current, max}` | HP, Mana |
| `RES_TRACK` | `[bool, bool...]` | Stress, Wounds |
| `VAL_STEP_DIE` | `string` | "d6", "d8" (Savage Worlds) |
| `CONT_LIST` | `[{name, qty}...]` | Inventory |

**Logic:**
1.  **Formulas:** Defined in Manifest (`AC = 10 + dex_mod`). Calculated automatically.
2.  **Invariants:** Defined by Prefab (Current <= Max). Enforced automatically.

## Documentation Map

- **`app/prefabs/`**: The core logic for the "Lego Protocol" (Manifests/Validation).
- **`app/tools/handlers/`**: The atomic tool implementations.
- **`app/gui/`**: NiceGUI frontend components.
- **`app/setup/`**: Logic for the "Session Zero" wizard and rule extraction.