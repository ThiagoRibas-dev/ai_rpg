### Master Summary of Proposed Improvements

| Component | Current State | Proposed Improvement | Benefit |
| :--- | :--- | :--- | :--- |
| **State Storage & Schemas** | Generic, schema-less JSON blobs in the `game_state` table. | **Schema-validated JSON** based on session-specific "Entity Templates" generated during SETUP. | **Consistency & Safety.** Prevents AI errors, enforces game rules automatically, and enables dynamic, context-aware tooling. |
| **NPC & Relationship Depth** | NPCs are basic "character" entities. Relationships are simple, single-word strings (e.g., "hostile"). | Introduce a linked **`npc_profile`** for personality/motivations. Evolve the `relationships` field into a **structured object with numerical scores** (Trust, Attraction) and descriptive tags. | **Dramatically improved roleplaying.** Gives the AI specific, targeted guidance for each NPC, making their behavior mechanically grounded and emotionally nuanced. |
| **Scene & Party Management** | The system tracks individual entities only. Group cohesion (e.g., a party in a room) is implicit and managed manually by the AI. | Create a **"Scene" entity** to group active participants in a location. Introduce atomic, group-based tools like `scene.move_to(...)`. | **Simpler & Safer AI.** Prevents state inconsistencies (e.g., party members getting separated), simplifies the AI's logic, and enables scene-wide effects. |
| **Entity Interaction (Tooling)** | Heavy reliance on the powerful but low-level `state.apply_patch` tool for many state changes. | Create **high-level, intent-based tools** like `inventory.add_item`, `quest.update_objective`, etc., abstracting away the JSON structure. | **Reduced AI Burden.** The AI's job is easier and less error-prone. It can focus on "what" to do, not "how" to format a complex JSON patch. |
| **Lore & World Knowledge** | Two separate systems: `World Info` (keyword-based) and `memories` with `kind="lore"` (semantic search). | **Unify into a single `memories` system.** All lore becomes a `memory` of `kind="lore"`, benefiting from the advanced retrieval logic. | **Player Agency & Simplicity.** Creates a single source of truth for lore that the player can directly see and **edit**, turning it into a collaborative "Lorebook" and simplifying the architecture. |
| **Entity Creation** | New entities are created via initial scaffolding or complex, multi-step tool calls. | Add a dedicated **`entity.create` tool**, validated against the session's Entity Templates. | **Dynamic World.** Empowers the AI to be a true world-builder, populating the game with new characters, items, and locations on the fly as the player explores. |
| **Memory & Temporal Context** | Memory has an unused `fictional_time` field. Retrieval is based on general relevance. | 1. Fully implement **`fictional_time`** for chronological awareness. 2. Implement **Relationship-Based Retrieval,** boosting the score of memories related to characters currently in the scene. | **Emotional Continuity.** Enables chronological reasoning ("What happened yesterday?") and ensures the most personally relevant memories are always surfaced, maintaining sharp, personal context even in long games. |
| **World Persistence & Agency** | The world is static. State only changes in direct response to player actions. | Implement **NPC Directives** (simple goals). Create a **"World Tick"** system that simulates NPC actions and world events during significant time skips. | **A Living World.** The world progresses "off-screen," generating emergent story hooks and making the game feel more dynamic, persistent, and alive. |


High-level specification documents for each of the proposed components.
---

### 1. Spec: Schema-Validated State Storage

*   **Goal:** To enforce data consistency for all game entities by validating them against a session-specific schema defined during SETUP mode.
*   **Affected Systems:**
    *   `app/core/turn_manager.py`
    *   `app/tools/executor.py`
    *   Tools that write state (e.g., `entity.create`, `state.apply_patch`).
*   **Implementation Steps:**
    [ ] 1.  **Load Manifest:** In `TurnManager`, at the start of `execute_turn`, load the session's `template_manifest` (the JSON schema) into a readily accessible object.
    [ ] 2.  **Create Validation Service:** Implement a new utility class or function, `StateValidator`, that can take an entity's data (a dictionary) and its `entity_type`, and validate it against the corresponding schema from the manifest. Pydantic can be used for this by dynamically creating models from the manifest schema.
    [ ] 3.  **Intercept State Writes:** Modify `ToolExecutor.execute`. Before executing a tool that modifies `game_state`, it must perform a validation check.
    [ ] 4.  **Validation Logic:**
        *   For a new `entity.create` tool, the `data` payload is validated directly.
        *   For `state.apply_patch`, the logic is: fetch the current entity state, apply the patch *in-memory* to get the new proposed state, and then validate the *resulting* state object.
    [ ] 5.  **Error Handling:** If validation fails, the `ToolExecutor` should not execute the tool. Instead, it must return an error result to the AI (e.g., `{"error": "Validation failed for 'character:player': missing required field 'attributes.hp_max'"}`). This forces the AI to correct its tool call on the next attempt.
*   **Example Data Structure:** The `template_manifest` will serve as the source for validation rules.
    ```json
    // In template_manifest (simplified)
    "character": {
      "type": "object",
      "properties": {
        "name": {"type": "string"},
        "attributes": {"type": "object", "properties": {"hp_current": {"type": "integer"}}}
      },
      "required": ["name", "attributes"]
    }
    ```

---

### 2. Spec: NPC & Relationship Depth

*   **Goal:** To give NPCs richer personalities and track the quality of their relationships with other entities, making AI roleplaying more consistent and mechanically grounded.
*   **Affected Systems:**
    *   `app/models/entities.py` (or a new file for `NpcProfile` model)
    *   `app/context/context_builder.py`
    *   `app/tools/schemas.py` and `app/tools/builtin/` for new tools.
*   **Implementation Steps:**
    [ ] 1.  **Define New Models:** Create new Pydantic models: `RelationshipStatus` (with fields like `trust: int`, `attraction: int`, `fear: int`, `tags: List[str]`) and `NpcProfile` (with `personality_traits`, `motivations`, and `relationships: Dict[str, RelationshipStatus]`).
    [ ] 2.  **Store as an Entity:** The `NpcProfile` will be stored in the `game_state` table with `entity_type="npc_profile"` and an `entity_key` matching the character it describes (e.g., `"kherchukhic"`).
    [ ] 3.  **Update Context Builder:** In `ContextBuilder.build_dynamic_context`, add a new step. If an NPC is identified as "active" in the scene, fetch its corresponding `npc_profile` from the `game_state` table. Format this data into a new, clearly marked context block (e.g., `# NPC PROFILE: Kherchukhic #`).
    [ ] 4.  **Create New Tool:** Implement a new tool, `npc.adjust_relationship(npc_key: str, subject_key: str, trust_change: int = 0, ...)`. The handler for this tool will use `state.apply_patch` internally to safely increment or decrement the numerical values in the `RelationshipStatus` object.
*   **Example Data Structure:**
    ```json
    // In game_state for entity_key="kherchukhic", entity_type="npc_profile"
    {
      "personality_traits": ["prideful", "curious", "solitary"],
      "motivations": ["Understand the world beyond her solitude"],
      "relationships": {
        "player": {
          "status": "intimate", "trust": 8, "attraction": 9, "fear": 1, "tags": ["protective"]
        }
      }
    }
    ```

---

### 3. Spec: Scene & Party Management

*   **Goal:** To manage groups of characters as a single unit, preventing state inconsistencies and simplifying the AI's logic for group actions.
*   **Affected Systems:**
    *   `app/tools/schemas.py` and `app/tools/builtin/`
    *   `app/context/context_builder.py`
    *   `app/core/turn_manager.py`
*   **Implementation Steps:**
    [ ] 1.  **Define Scene Entity:** A `Scene` entity will be stored in `game_state` with `entity_type="scene"` and `entity_key="current_encounter"`. Its `state_data` will contain a `location_key` and a `members` list of character entity keys (e.g., `["character:player", "character:kherchukhic"]`).
    [ ] 2.  **Create Scene Tools:** Implement a suite of tools for scene management:
        *   `scene.add_member(character_key)`
        *   `scene.remove_member(character_key)`
        *   `scene.move_to(new_location_key)`
    [ ] 3.  **Implement Atomic `move_to` Handler:** The handler for `scene.move_to` is critical. It must be an atomic operation: it fetches the `scene` entity, iterates through the `members` list, and for each member, it executes a `state.apply_patch` to update their individual `location_key`. This ensures the whole group moves together.
    [ ] 4.  **Update Context Builder:** The `ContextBuilder` should now start by fetching the `"current_encounter"` scene to know who is present. This information will drive the retrieval of `NpcProfile`s and the relationship-based memory scoring.
*   **Example Data Structure:**
    ```json
    // In game_state for entity_key="current_encounter", entity_type="scene"
    {
      "location_key": "dragons_tooth_plateau",
      "members": ["character:player", "character:kherchukhic"],
      "scene_state": ["reunion", "intimate"]
    }
    ```

---

### 4. Spec: High-Level, Intent-Based Tools

*   **Goal:** To simplify the AI's task by abstracting away complex JSON structures into simple, intent-driven tool calls.
*   **Affected Systems:**
    *   `app/tools/schemas.py`
    *   `app/tools/builtin/` directory.
*   **Implementation Steps:**
    [ ] 1.  **Identify Common Patterns:** Review AI logs to find the most frequent use-cases for the `state.apply_patch` tool (e.g., adding/removing from inventory, updating quest objectives).
    [ ] 2.  **Design High-Level Schemas:** For each pattern, create a new, simple Pydantic schema in `tools/schemas.py`. For example, `InventoryAddItem(owner_key: str, item_name: str, quantity: int)`.
    [ ] 3.  **Implement Handlers as Translators:** Create a corresponding handler file in `tools/builtin/`. The handler's job is to take the simple arguments (like `item_name`) and translate them into the correct, complex `state.apply_patch` call. This encapsulates the implementation details.
    [ ] 4.  **Update AI Prompts:** In the system prompt or tool descriptions, guide the AI to prefer these new high-level tools over the low-level `state.apply_patch` for common tasks.
*   **Example:**
    *   **Before (AI's Task):** `state.apply_patch(entity_type="inventory", key="player", patch=[{"op": "add", "path": "/items/-", "value": {"name": "Health Potion", "quantity": 1}}])`
    *   **After (AI's Task):** `inventory.add_item(owner_key="player", item_name="Health Potion", quantity=1)`

---

### 5. Spec: Unified Lore System

*   **Goal:** To merge the `World Info` system into the `memories` system, creating a single, powerful, and player-editable source of truth for all lore.
*   **Affected Systems:**
    *   `app/context/context_builder.py`
    *   `app/context/world_info_service.py` (for deprecation)
    *   `app/gui/world_info_manager_view.py` (major refactor)
    *   Associated database repositories.
*   **Implementation Steps:**
    [ ] 1.  **Data Migration:** Create a one-time script to migrate all existing `world_info` entries into the `memories` table, setting their `kind` to `"lore"` and converting their `keywords` into `tags`.
    [ ] 2.  **Deprecate Old System:** Remove the call to `world_info.search_for_history` from `ContextBuilder`. The `MemoryRetriever` will now handle the retrieval of these `lore` memories automatically. Delete the `WorldInfoService` and its repository.
    [ ] 3.  **Refactor GUI:** Rename `WorldInfoManagerView` to `LorebookView`.
        *   Change its data source to query the `memories` table for `kind='lore'`.
        *   Update its UI to map to the `Memory` model: the "Keywords" field becomes "Tags," and a new "Priority" slider should be added.
        *   The save/create/delete buttons should now call the `memory.update`/`upsert`/`delete` tools (or their repository equivalents).
*   **Benefit:** The player gains direct control over the game's canon through a simple UI, and the backend architecture is simplified.

---

### 6. Spec: Dynamic Entity Creation

*   **Goal:** To empower the AI to dynamically create new characters, items, and other entities during gameplay.
*   **Affected Systems:**
    *   `app/tools/schemas.py` and `app/tools/builtin/`
    *   Relies on the `StateValidator` from Spec #1.
*   **Implementation Steps:**
    [ ] 1.  **Create Tool Schema:** Define a new Pydantic schema `EntityCreate(entity_type: str, entity_key: str, data: dict)` in `tools/schemas.py`.
    [ ] 2.  **Create Handler:** Implement the `entity_create.py` handler in `tools/builtin/`.
    [ ] 3.  **Handler Logic:** The handler's primary responsibility is validation. It will call the `StateValidator` (from Spec #1) to check the provided `data` payload against the `template_manifest` for the given `entity_type`.
    4.  If validation passes, the handler calls `db_manager.game_state.set_entity` to create the new record.
    5.  If validation fails, it returns a descriptive error to the AI.
*   **Example Tool Call:** `entity.create(entity_type="character", entity_key="goblin_scout_3", data={"name": "Gribble", "attributes": ...})`

---

### 7. Spec: Enhanced Memory & Temporal Context

*   **Goal:** To make the AI aware of event chronology and to prioritize memories related to the current social context.
*   **Affected Systems:**
    *   `app/context/memory_retriever.py`
    *   `app/tools/builtin/memory_upsert.py` handler
    *   `app/core/turn_manager.py`
*   **Implementation Steps:**
    [ ] 1.  **Implement Fictional Time:**
        *   In `TurnManager`, ensure `current_game_time` from the `GameSession` is consistently passed into the `ToolExecutor`'s context dictionary.
        *   In the `memory.upsert` handler, retrieve `current_game_time` from the context and pass it to the `db_manager.memories.create` method.
        *   In `MemoryRetriever.format_for_prompt`, modify the string formatting to include the `fictional_time` if it exists on a memory.
    [ ] 2.  **Implement Relationship-Based Retrieval:**
        *   Modify `MemoryRetriever.get_relevant`. It will now need the list of active scene members as an argument, which the `TurnManager` must provide.
        *   Inside the scoring loop, add a new condition: iterate through the scene members' keys. If a memory's tags contain a member's key (e.g., a memory tagged `"kherchukhic"` when she is in the scene), apply a significant bonus to its score.
*   **Example Context String:**
    *   **Before:** `ðŸ“– [Episodic] (Priority: â˜…â˜…â˜…â˜…â˜…, ID: 42) [reunion]`
    *   **After:** `ðŸ“– [Episodic] (Priority: â˜…â˜…â˜…â˜…â˜…, ID: 42) [reunion] (Time: Day 44, Afternoon)`

---

### 8. Spec: World Persistence & Agency

*   **Goal:** To create the illusion of a living world by simulating "off-screen" NPC actions and events during time skips.
*   **Affected Systems:**
    *   `NpcProfile` model.
    *   `app/core/turn_manager.py`
    *   `app/tools/builtin/time_advance.py` handler.
*   **Implementation Steps:**
    [ ] 1.  **Add `directive` Field:** Add an optional `directive: str` field to the `NpcProfile` model (e.g., `"Patrol the northern border"`).
    [ ] 2.  **Create Simulation Logic:** Implement a new private method, `_execute_world_tick(duration)`, in `TurnManager`. This method will:
        *   Fetch all `npc_profile` entities that have a non-empty `directive`.
        *   For each NPC, perform a simple, abstract check (e.g., a random roll modified by the NPC's skills) to determine if they made progress on their directive.
        *   If the check is successful, it will call `memory.upsert` to create a new `episodic` memory summarizing the off-screen event, using the appropriate `fictional_time`.
    [ ] 3.  **Trigger the Tick:** Modify the `time.advance` tool's handler. When called, it should check the duration of the time skip. If it's longer than a predefined threshold (e.g., 6 hours), it should call the `_execute_world_tick` method, passing in the duration.
*   **Example `directive`:**
    ```json
    // In NpcProfile for "baron_von_hess"
    "directive": "Gather political support to overthrow the king."
    ```