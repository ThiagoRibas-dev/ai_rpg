### Phase 1: Foundation (Connector & Super Tools)
**Goal:** Enable "Thought + Action" responses and consolidate the toolset to reduce cognitive load on the model.

- [x] **1.1. Refactor `LLMConnector` Interface**
    - [x] Modify `get_tool_calls` (or create `chat_with_tools`) to return a data structure containing **both** `content` (text/thoughts) and `tool_calls` (list).
    - [x] Update `OpenAIConnector` to capture `response.choices[0].message.content`.
    - [x] Update `GeminiConnector` to capture the text part alongside function calls.

- [x] **1.2. Implement `entity.update` (The State Super-Tool)**
    - [x] Create schema in `schemas.py`: Accepts `target_key` and a dictionary of `changes` (e.g., `{"hp": -5, "inventory": {"add": "Sword"}}`).
    - [x] Create handler in `tools/builtin/entity_update.py`.
    - [x] Implement logic to route specific keys (vital changes trigger death checks; inventory changes route to slot logic).

- [x] **1.3. Implement `game.roll` (The Dice Super-Tool)**
    - [x] Create schema: Accepts `formula` (e.g., "1d20+5") and `reason` (text for logging).
    - [x] Create handler: Wraps the existing RNG logic but standardizes the output format for the chat history.

- [x] **1.4. Implement `world.travel` (The Movement Super-Tool)**
    - [x] Create schema: Accepts `destination_key`.
    - [x] Create handler: Merges logic from `scene.move_to` and `location.create` (lazy creation if destination is new/implied).

- [x] **1.5. Implement `game.log` (The Memory Super-Tool)**
    - [x] Merge `memory.upsert` and `journal.add_entry` into a single tool for recording facts/events.

---

### Phase 2: The Core ReAct Loop
**Goal:** Replace the "Plan -> Execute" waterfall with the "Reason -> Act" iterative loop.

- [x] **2.1. Create `ReActTurnManager`**
    - [x] Scaffold a new method/class to handle the turn execution.
    - [x] Implement the `while` loop (Max iterations: ~5).

- [x] **2.2. Implement "Action Mode" (Phase A)**
    - [x] Configure the API call to include the "Super Tools".
    - [x] Implement the logic:
        - If `content` exists: Append to history as **Thought** (Assistant role).
        - If `tool_calls` exist: Execute via `ToolExecutor`, append result as **Tool** role.
        - If **no** tools called: Break the loop (transition to Narrative).

- [x] **2.3. Implement "Narrative Mode" (Phase B)**
    - [x] Configure a final API call with **Tools Disabled** (force text).
    - [x] Append the **Steering Prefill** (e.g., `{"role": "assistant", "content": "[Narrating the scene]"}`) to the history to force the style change.
    - [x] Stream the result to the UI.

- [x] **2.4. Update `Orchestrator`**
    - [x] Wire the `plan_and_execute` entry point to use the new `ReActTurnManager`.

---

### Phase 3: Context Optimization
**Goal:** Remove heavy raw data from the prompt and replace it with calculated semantic tags.

- [x] **3.1. Refactor `ContextBuilder`**
    - [x] Remove `_run_jit_simulation` call (move to Phase 4).
    - [x] Remove raw JSON dumps of Inventory and Statblocks. Only inject "Active Scene" summary and "Player Vitals".

- [x] **3.2. Implement Python-Side Spatial Awareness**
    - [x] In `ContextBuilder`, retrieve coordinates for all actors in the scene.
    - [x] Calculate distances relative to the player using `math.dist`.
    - [x] Inject a "Relative Positions" block into the prompt (e.g., `Goblin: 15ft (Near)`).

- [x] **3.3. Optimize JIT Simulation Triggers**
    - [x] Remove the "Every Turn" check.
    - [x] Add JIT logic hooks into the `world.travel` and `time.advance` tool handlers (only simulate when context shifts).

---

### Phase 4: Cleanup & UI Synchronization
**Goal:** Ensure the UI reflects the new flow and remove dead code.

- [x] **4.1. Update UI Queue Handler**
    - [x] Ensure "Thoughts" (text received during Action Mode) are displayed in the UI (e.g., as greyed-out "Thinking..." text or a collapsible bubble).
    - [x] Ensure the final Narrative stream replaces or follows the thoughts clearly.

- [x] **4.2. Update System Prompts**
    - [x] Replace complex JSON schemas in `templates.py` with a simple "Game Master Persona" prompt.
    - [x] Remove specific instructions about "Auditing" or "Planning".

- [x] **4.3. Delete Legacy Services**
    - [x] Delete `PlannerService.py`.
    - [x] Delete `AuditorService.py`.
    - [x] Delete `NarratorService.py` (merged into the ReAct loop).
    - [x] Delete the 20+ unused granular tool files.
