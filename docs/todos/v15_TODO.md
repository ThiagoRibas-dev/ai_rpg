### **Phase 1: Tooling Infrastructure & Safety (The Engine)**
**Goal:** Remove dangerous generic tools and prepare the registry for domain-specific logic.

- [ ] **1.1. Clean House (Deprecations)**
    *   **Action:** Delete or move the following files to a `_deprecated` folder.
    *   **Files:**
        *   `app/tools/builtin/state_apply_patch.py` (Too dangerous for gameplay).
        *   `app/tools/builtin/entity_create.py` (Too unstructured).
        *   `app/tools/builtin/quest_update_objective.py` (Will be replaced by Journal).
    *   **Note:** Keep `state.query` and `schema.query`; reading data is safe and necessary.

- [ ] **1.2. Restrict `character.update`**
    *   **File:** `app/tools/builtin/character_update.py`
    *   **Logic:** Add a check at the top of the handler. If `session.game_mode == "GAMEPLAY"`, reject changes to core stats (STR, DEX) or derived stats. Only allow specific fields if absolutely necessary, or deprecate entirely in favor of `modify_stat`.
    *   **Code:**
        ```python
        if context.get("game_mode") == "GAMEPLAY":
            # Allow only flavor text updates, or reject entirely
            pass
        ```

---

### **Phase 2: The Location Graph (The Environment)**
**Goal:** Ground the AI in a strict spatial network to prevent teleportation and hallucinations.

- [ ] **2.1. Implement `LocationCreate` Tool**
    *   **File:** `app/tools/builtin/location_create.py`
    *   **Goal:** Enforce visual fields for the UI.
    *   **Schema:**
        ```python
        class LocationCreate(BaseModel):
            name: Literal["location.create"] = "location.create"
            key: str = Field(..., description="Unique ID (e.g., 'crypt_entrance').")
            name_display: str = Field(..., description="Display name (e.g., 'The Crypt Mouth').")
            description_visual: str = Field(..., description="Visuals: lighting, architecture, layout.")
            description_sensory: str = Field(..., description="Smell, sound, temperature.")
            type: Literal["indoor", "outdoor", "dungeon", "city"]
        ```

- [ ] **2.2. Implement `LocationConnect` Tool**
    *   **File:** `app/tools/builtin/location_connect.py`
    *   **Goal:** Create edges between nodes. Handle bi-directionality automatically.
    *   **Logic:**
        1.  Load `from_loc` and `to_loc`.
        2.  Update `from_loc["connections"][direction] = { target: to_key, ... }`.
        3.  If `not one_way`, update `to_loc["connections"][back_direction] = { target: from_key, ... }`.

- [ ] **2.3. Refactor `scene.move_to` (Validation)**
    *   **File:** `app/tools/builtin/scene_move_to.py`
    *   **Logic:**
        1.  Get `active_scene` -> `current_location_key`.
        2.  Load `current_location` entity.
        3.  Check if `destination_key` exists in `current_location["connections"]`.
        4.  **If Invalid:** Return error: *"You cannot move there directly. No connection exists."*
        5.  **If Valid:** Update `active_scene` and return `{"ui_event": "location_change", "new_loc": ...}`.

- [ ] **2.4. Context Injection (The HUD)**
    *   **File:** `app/context/context_builder.py`
    *   **Logic:** In `build_dynamic_context`, fetch the current location and format the connections for the System Prompt.
    *   **Format:**
        ```text
        [CURRENT LOCATION: The Crypt Mouth]
        (Visual Description...)
        [EXITS]
        - North -> Dark Hallway (crypt_hall_1) [LOCKED]
        - South -> Forest Path (forest_clearing)
        ```

---

### **Phase 3: Simulation Logic (The Physics)**
**Goal:** Python handles the math. AI handles the intent.

- [ ] **3.1. Implement `CharacterApplyDamage`**
    *   **File:** `app/tools/builtin/character_apply_damage.py`
    *   **Logic:**
        ```python
        # Pseudocode
        target = get_entity(...)
        current_hp = target["vitals"]["HP"]["current"]
        new_hp = current_hp - amount
        target["vitals"]["HP"]["current"] = new_hp
        
        status = "Healthy"
        if new_hp <= 0:
            status = "Unconscious/Dead"
            # Auto-apply condition
            target["conditions"].append("Unconscious")
        
        return {"damage": amount, "remaining": new_hp, "status": status}
        ```

- [ ] **3.2. Implement `CharacterRestoreVital`**
    *   **File:** `app/tools/builtin/character_restore_vital.py`
    *   **Logic:** Heal, but clamp to `max` value defined in the schema.

- [ ] **3.3. Implement `NpcSpawn`**
    *   **File:** `app/tools/builtin/npc_spawn.py`
    *   **Goal:** "Introduce" characters properly so the UI can render them.
    *   **Schema:**
        ```python
        class NpcSpawn(BaseModel):
            key: str
            name_display: str
            visual_description: str # For UI Tooltip
            stat_template: str # "Goblin", "Guard"
            initial_disposition: str
        ```
    *   **Logic:** Create entity -> Add to `active_scene` members list immediately.

---

### **Phase 4: Narrative Memory (The Brain)**
**Goal:** Solve context amnesia using Scenes and Summaries.

- [ ] **4.1. Database Schema Update**
    *   **File:** `app/database/repositories/turn_metadata_repository.py`
    *   **Action:** Create a new table `scene_history`.
    *   **Columns:** `id`, `session_id`, `location_key`, `summary_text`, `start_turn`, `end_turn`.

- [ ] **4.2. Implement Summarization Trigger**
    *   **File:** `app/core/turn_manager.py`
    *   **Logic:**
        1.  Inside `execute_turn`, check if `scene.move_to` was called successfully.
        2.  If yes, identify the *previous* location/scene.
        3.  Gather all `turn_metadata` (user/assistant text) since the last move.
        4.  **LLM Call:** Send to LLM with Waidrin's "Summarize Scene" prompt.
        5.  Save result to `scene_history` table.

- [ ] **4.3. Update Context Builder**
    *   **File:** `app/context/context_builder.py`
    *   **Logic:**
        1.  `history_text` = Fetch last 3 rows from `scene_history`.
        2.  `current_scene_text` = Fetch raw chat messages *since* the last scene change.
        3.  Combine: `[STORY SO FAR]\n{history_text}\n\n[CURRENT SCENE]\n{current_scene_text}`.

- [ ] **4.4. Implement `JournalAddEntry`**
    *   **File:** `app/tools/builtin/journal_add_entry.py`
    *   **Goal:** Track quests/clues explicitly.
    *   **Schema:** `title`, `content`, `is_secret`.

---

### **Phase 5: UI/UX Enhancements (The Interface)**
**Goal:** Make the game visual and interactive.

- [ ] **5.1. Implement `LocationCard` Widget**
    *   **File:** `app/gui/managers/chat_bubble_manager.py`
    *   **Logic:**
        *   Listen for `{"type": "location_change", "data": ...}` in UI queue.
        *   Render a `CTkFrame` spanning the width of the chat.
        *   **Visuals:** Bold Title, Italic Visual Description. Maybe an icon based on `type` (cave/city/etc).

- [ ] **5.2. Implement Navigation Buttons**
    *   **File:** `app/gui/managers/ui_queue_handler.py` & `app/gui/main_view.py`
    *   **Logic:**
        *   In `ui_queue_handler`, when a turn ends, look at the `active_scene` location's connections.
        *   Emit `{"type": "update_nav", "exits": ["North", "Up"]}`.
        *   In `MainView`, update a button bar below the chat input.
        *   Clicking "North" -> Sends "I go North" to input.

- [ ] **5.3. Interactive Text (Entity Tooltips)**
    *   **File:** `app/gui/managers/chat_bubble_manager.py`
    *   **Action:**
        *   Parse text for `**Name**`.
        *   Use `CTkLabel` or `Tkinter Text` tags to make them clickable.
        *   On click -> Open `InspectorManager` for that entity.

- [ ] **5.4. The Setup Wizard**
    *   **File:** `app/gui/panels/setup_wizard.py`
    *   **Action:** Create a modal that runs *before* `Orchestrator.start`.
    *   **Steps:**
        1.  Genre Select.
        2.  World Gen (LLM Call).
        3.  Player Gen (LLM Call).
        4.  Start Game (Commits to DB, initializes `active_scene`).

---

### **Phase 6: The Auditor Safety Net (The Guardrail)**
**Goal:** Ensure the LLM actually uses the new tools.

- [ ] **6.1. Update Auditor Prompts**
    *   **File:** `app/llm/auditor_service.py`
    *   **Prompt Additions:**
        *   "Did the narrative describe moving to a new place? If so, was `scene.move_to` called?"
        *   "Did the narrative describe damage or healing? If so, was `character.apply_damage` called?"
    *   **Auto-Correction:** If the tool was missed but the narrative implies it, the Auditor should propose executing that tool immediately.