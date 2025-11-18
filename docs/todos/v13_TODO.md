Here is the implementation checklist, broken down into logical phases. This moves the system from a monolithic "Simulationist" schema to the flexible **Ruleset + StatBlock** architecture.

### Phase 1: Data Modeling & Database (The Foundation)
*Goal: Define the new data structures and prepare the database to store them.*

- [x] **1. Create New Pydantic Models (`app/models/ruleset.py`)**
    - [x] Define `Ruleset` root model.
    - [x] Define `Compendium` (dictionaries for skills, conditions, items).
    - [x] Define `RuleEntry` (for text-based rules like "Grappling").
- [x] **2. Create New Pydantic Models (`app/models/stat_block.py`)**
    - [x] Define `StatBlockTemplate` root model.
    - [x] Define `AbilityDef` (support `data_type`: "integer", "die_code", "dots").
    - [x] Define `VitalDef` (Resource pools with min/max/recover).
    - [x] Define `TrackDef` (Clocks/Progress bars).
    - [x] Define `SlotDef` (Containers with capacity/filters).
- [x] **3. Update Database Schema (`app/database/repositories/`)**
    - [x] Create `ruleset_repository.py`: Table `rulesets` (id, name, json_data).
    - [x] Create `stat_template_repository.py`: Table `stat_templates` (id, ruleset_id, name, json_data).
    - [x] **Migration:** Update `sessions` table to link to a `ruleset_id`.
    - [x] **Migration:** Update `game_state` entities to link to a `stat_template_id` (so the validator knows which template to check against).
- [x] **4. Refactor `DBManager`**
    - [x] Register the new repositories in `__enter__`.
    - [x] Update table creation scripts.

### Phase 2: AI Extraction Logic (The Input)
*Goal: Update the setup phase to generate these new structures from rulebooks.*

- [x] **1. Update Prompts (`app/prompts/templates.py`)**
    - [x] Create `GENERATE_RULESET_PROMPT`: Focus on resolution mechanics, text rules, and the "Compendium" (lists of skills/conditions).
    - [x] Create `GENERATE_STATBLOCK_PROMPT`: Focus on the *structure* of a PC (Attributes, Vitals, Slots).
- [x] **2. Update Generation Service (`app/setup/template_generation_service.py`)**
    - [x] Refactor `generate_template()` to run in two distinct stages:
        1.  **Global Extraction:** Produce the `Ruleset`.
        2.  **Template Construction:** Produce the `StatBlockTemplate` (using the Ruleset as context).
    - [x] Ensure "Dice Codes" (d4, d6) are recognized as valid types during extraction.
- [x] **3. Update Setup Manifest (`app/setup/setup_manifest.py`)**
    - [x] Track `ruleset_id` and `pc_template_id` instead of the old generic manifest.

### Phase 3: Runtime Logic & Validation (The Brain)
*Goal: Teach the system how to enforce the new rules.*

- [x] **1. Refactor `StateValidator` (`app/utils/state_validator.py`)**
    - [x] **Init:** Load `StatBlockTemplate` instead of the old manifest.
    - [x] **Validation Logic:**
        - [x] `_validate_ability`: Allow strings if type is `die_code` (Regex check: `^d[4,6,8,10,12,20]$`).
        - [x] `_validate_track`: Ensure updates don't exceed `max_segments`.
        - [x] `_validate_slot`: Check capacity (count or weight) before allowing an add.
- [x] **2. Update `character.update` Tool**
    - [x] Handle `Track` updates (increment/decrement logic).
    - [x] Handle `Vital` updates (clamping to Min/Max defined in template).
- [x] **3. Update `inventory.add_item` Tool**
    - [x] Check the target `Slot` definition.
    - [x] Enforce `capacity` limits defined in the `StatBlockTemplate`.
    - [x] Enforce `filter` logic (e.g., "Cyberware slot only accepts items with tag 'cyberware'").

### Phase 4: Context Injection (The Interface)
*Goal: Ensure the LLM sees the rules and the character sheet correctly.*

- [x] **1. Update Context Builder (`app/context/context_builder.py`)**
    - [x] `build_static_system_instruction`: Inject the `Ruleset` summary (Core Resolution + Action Economy).
    - [x] `build_dynamic_context`: Inject the specific character's `StatBlock` state.
- [x] **2. Optimize Token Usage**
    - [x] *Optimization:* Only inject the `Compendium` definitions (e.g., specific Spell text) if they are currently relevant (RAG search or Active Inventory), rather than dumping the whole rulebook.

### Phase 5: GUI Visualization (The Visuals)
*Goal: Make the new data types visible to the player.*

- [x] **1. Update Character Inspector (`app/gui/panels/inspectors/character_inspector.py`)**
    - [x] **Abilities:** Render generic values (Integer or String/Die Code).
    - [x] **Vitals:** Render standard bars (Current/Max).
    - [x] **Tracks (NEW):** Render Clocks (Pie charts using `ctk` canvas or simple text `(â— â— â—‹â—‹)`) or Checkboxes.
- [x] **2. Update Inventory Inspector**
    - [x] Group items by **Slot** (e.g., "Backpack", "Belt", "Memory Units") instead of one big list.
    - [x] Show Capacity usage per slot (e.g., "Backpack: 15/20 lbs").

### Phase 6: Integration Repair
*Goal: Perform the critical "wiring" to make the new data structures actually work at runtime.*

- [x] **1. Update `app/tools/executor.py`**: Remove the `StateValidator` initialization and the `if isinstance(call, schemas.StateApplyPatch)` validation block. Let the specific tools handle validation.
- [x] **2. Update `app/setup/scaffolding.py`**: Rewrite `inject_setup_scaffolding` to accept `ruleset_id` and `stat_template_id`. Construct the initial `player` entity using the *StatBlockTemplate* structure, not the old hardcoded classes.
- [x] **3. Update `app/models/entities.py`**: Delete this file. It is legacy code. The "Entity" is now just a dynamic Dictionary stored in JSON, shaped by the `StatBlockTemplate`.
- [x] **4. Update `app/tools/builtin/entity_create.py`**: Add `template_name` to the schema arguments. Lookup the template from the DB before validating.
- [x] **5. Update `app/gui/managers/session_manager.py`**: In `new_game`, when calling `inject_setup_scaffolding`, pass the `ruleset_id` and `stat_template_id` derived from the prompt's `template_manifest`. (You might need to parse the manifest JSON in `new_game` to get these IDs).
- [x] **6. Update `app/database/repositories/ruleset_repository.py`**: Ensure it returns the database ID upon creation (needed for linking).
- [x] **7. Update `app/tools/schemas.py`**: Add `template_name` to the `EntityCreate` schema.
