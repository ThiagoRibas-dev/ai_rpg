## Master Summary of Proposed Improvements

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


#### **Spec: Unified Lore System**

*   **Status:** **COMPLETE.** All application code has been refactored. The old `WorldInfo` system is fully deprecated in favor of a unified `memory` system where `kind='lore'`. The player-facing "Lorebook" is now functional.
*   **Implementation Steps:**
    *   [x] **Deprecate Old System:** `WorldInfoService` has been removed from `ContextBuilder` and `TurnManager`.
    *   [x] **Refactor GUI:** `WorldInfoManagerView` has been renamed and refactored into `LoreEditorView`, now operating on the `memories` table for `kind='lore'`.

#### **Spec (Part 1): Fictional Time Implementation**

*   **Status:** **COMPLETE.** The system for tracking and retrieving memories by in-game time is fully implemented.
*   **Implementation Steps:**
    *   [x] **Pass Time to Context:** `TurnManager` correctly passes `current_game_time` to the `ToolExecutor`.
    *   [x] **Timestamp Memories:** The `memory.upsert` handler now automatically applies the `fictional_time` to new memories.
    *   [x] **Display Timestamp:** `MemoryRetriever` now includes the `fictional_time` in the context string sent to the AI.
    *   [x] **Enable Time Queries:** The `MemoryQuery` tool and its handler now support filtering by `time_query`.

#### **Spec: Schema-Validated State Storage (Foundation)**

*   **Goal:** To enforce data consistency for all game entities by validating them against a session-specific schema.
*   **Implementation Steps:**
    [x] 1.  **Load Manifest:** In `TurnManager`, load the session's `template_manifest` at the start of `execute_turn`.
    [x] 2.  **Create Validation Service:** Implement a `StateValidator` utility that can validate a dictionary against the manifest's schemas.
    [x] 3.  **Intercept State Writes:** Modify `ToolExecutor.execute` to perform validation checks before running state-modifying tools.
    [x] 4.  **Implement Validation Logic:** Handle validation for both `entity.create` and the results of `state.apply_patch`.
    [x] 5.  **Error Handling:** Ensure validation failures return a clear error message to the AI.

#### **Spec: NPC & Relationship Depth (Foundation)**

*   **Status:** **COMPLETE.** The core data models for NPC profiles and relationships are defined, the `npc.adjust_relationship` tool is implemented, and the `ContextBuilder` now exposes NPC profiles to the AI.
*   **Implementation Steps:**
    [x] 1.  **Define New Models:** Create `RelationshipStatus` and `NpcProfile` Pydantic models.
    [x] 2.  **Store as an Entity:** Ensure `NpcProfile` can be stored in the `game_state` table.
    [x] 3.  **Update Context Builder:** Modify `ContextBuilder` to fetch and display the `NpcProfile` for active characters.
    [x] 4.  **Create New Tool:** Implement the `npc.adjust_relationship` tool.

#### **Spec: Scene & Party Management (Foundation)**

*   **Goal:** To manage groups of characters as a single, atomic unit.
*   **Implementation Steps:**
    [x] 1.  **Define Scene Entity:** Determine the structure for the `Scene` entity in `game_state`.
    [x] 2.  **Create Scene Tools:** Implement `scene.add_member`, `scene.remove_member`, and `scene.move_to`.
    [x] 3.  **Implement Atomic `move_to` Handler:** Ensure the `scene.move_to` handler safely updates the location for all members.
    [x] 4.  **Update Context Builder:** Use the `Scene` entity to determine which characters are "active".

#### **Spec: High-Level, Intent-Based Tools**

*   **Goal:** To simplify the AI's job by abstracting away complex JSON structures.
*   **Implementation Steps:**
    [x] 1.  **Identify Common Patterns:** Review logs for common `state.apply_patch` uses (e.g., inventory management).
    [x] 2.  **Design High-Level Schemas:** Create simple schemas like `InventoryAddItem`.
    [x] 3.  **Implement Handlers as Translators:** Write handlers that convert simple inputs into the necessary `state.apply_patch` calls.
    [x] 4.  **Update AI Prompts:** Guide the AI to prefer the new, simpler tools.

#### **Spec: Dynamic Entity Creation**

*   **Goal:** To empower the AI to dynamically create new entities during gameplay.
*   **Implementation Steps:**
    [ ] 1.  **Create Tool Schema:** Define the `EntityCreate` schema.
    [ ] 2.  **Create Handler:** Implement the handler, ensuring it calls the `StateValidator` before writing to the database.

#### **Spec #7 (Part 2): Relationship-Based Memory Retrieval**

*   **Goal:** To prioritize memories related to the current social context.
*   **Implementation Steps:**
    [ ] 1.  **Update `get_relevant`:** Modify `MemoryRetriever.get_relevant` to accept a list of active scene members.
    [ ] 2.  **Implement Score Bonus:** Inside the scoring loop, apply a significant score bonus to memories whose tags match the entity keys of the characters present in the scene.

#### **Spec: World Persistence & Agency (Advanced)**

*   **Goal:** To create the illusion of a living world with "off-screen" progression.
*   **Implementation Steps:**
    [ ] 1.  **Add `directive` Field:** Add a `directive: str` field to the `NpcProfile` model.
    [ ] 2.  **Create Simulation Logic:** Implement a `_execute_world_tick(duration)` method in `TurnManager`.
    [ ] 3.  **Trigger the Tick:** Modify the `time.advance` tool's handler to call the tick function on long time skips.
