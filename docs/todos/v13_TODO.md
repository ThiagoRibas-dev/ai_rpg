Here is the implementation checklist, broken down into logical phases. This moves the system from a monolithic "Simulationist" schema to the flexible **Ruleset + StatBlock** architecture.

### Phase 1: Data Modeling & Database (The Foundation)
*Goal: Define the new data structures and prepare the database to store them.*

- [ ] **1. Create New Pydantic Models (`app/models/ruleset.py`)**
    - [ ] Define `Ruleset` root model.
    - [ ] Define `Compendium` (dictionaries for skills, conditions, items).
    - [ ] Define `RuleEntry` (for text-based rules like "Grappling").
- [ ] **2. Create New Pydantic Models (`app/models/stat_block.py`)**
    - [ ] Define `StatBlockTemplate` root model.
    - [ ] Define `AbilityDef` (support `data_type`: "integer", "die_code", "dots").
    - [ ] Define `VitalDef` (Resource pools with min/max/recover).
    - [ ] Define `TrackDef` (Clocks/Progress bars).
    - [ ] Define `SlotDef` (Containers with capacity/filters).
- [ ] **3. Update Database Schema (`app/database/repositories/`)**
    - [ ] Create `ruleset_repository.py`: Table `rulesets` (id, name, json_data).
    - [ ] Create `stat_template_repository.py`: Table `stat_templates` (id, ruleset_id, name, json_data).
    - [ ] **Migration:** Update `sessions` table to link to a `ruleset_id`.
    - [ ] **Migration:** Update `game_state` entities to link to a `stat_template_id` (so the validator knows which template to check against).
- [ ] **4. Refactor `DBManager`**
    - [ ] Register the new repositories in `__enter__`.
    - [ ] Update table creation scripts.

### Phase 2: AI Extraction Logic (The Input)
*Goal: Update the setup phase to generate these new structures from rulebooks.*

- [ ] **1. Update Prompts (`app/prompts/templates.py`)**
    - [ ] Create `GENERATE_RULESET_PROMPT`: Focus on resolution mechanics, text rules, and the "Compendium" (lists of skills/conditions).
    - [ ] Create `GENERATE_STATBLOCK_PROMPT`: Focus on the *structure* of a PC (Attributes, Vitals, Slots).
- [ ] **2. Update Generation Service (`app/setup/template_generation_service.py`)**
    - [ ] Refactor `generate_template()` to run in two distinct stages:
        1.  **Global Extraction:** Produce the `Ruleset`.
        2.  **Template Construction:** Produce the `StatBlockTemplate` (using the Ruleset as context).
    - [ ] Ensure "Dice Codes" (d4, d6) are recognized as valid types during extraction.
- [ ] **3. Update Setup Manifest (`app/setup/setup_manifest.py`)**
    - [ ] Track `ruleset_id` and `pc_template_id` instead of the old generic manifest.

### Phase 3: Runtime Logic & Validation (The Brain)
*Goal: Teach the system how to enforce the new rules.*

- [ ] **1. Refactor `StateValidator` (`app/utils/state_validator.py`)**
    - [ ] **Init:** Load `StatBlockTemplate` instead of the old manifest.
    - [ ] **Validation Logic:**
        - [ ] `_validate_ability`: Allow strings if type is `die_code` (Regex check: `^d[4,6,8,10,12,20]$`).
        - [ ] `_validate_track`: Ensure updates don't exceed `max_segments`.
        - [ ] `_validate_slot`: Check capacity (count or weight) before allowing an add.
- [ ] **2. Update `character.update` Tool**
    - [ ] Handle `Track` updates (increment/decrement logic).
    - [ ] Handle `Vital` updates (clamping to Min/Max defined in template).
- [ ] **3. Update `inventory.add_item` Tool**
    - [ ] Check the target `Slot` definition.
    - [ ] Enforce `capacity` limits defined in the `StatBlockTemplate`.
    - [ ] Enforce `filter` logic (e.g., "Cyberware slot only accepts items with tag 'cyberware'").

### Phase 4: Context Injection (The Interface)
*Goal: Ensure the LLM sees the rules and the character sheet correctly.*

- [ ] **1. Update Context Builder (`app/context/context_builder.py`)**
    - [ ] `build_static_system_instruction`: Inject the `Ruleset` summary (Core Resolution + Action Economy).
    - [ ] `build_dynamic_context`: Inject the specific character's `StatBlock` state.
- [ ] **2. Optimize Token Usage**
    - [ ] *Optimization:* Only inject the `Compendium` definitions (e.g., specific Spell text) if they are currently relevant (RAG search or Active Inventory), rather than dumping the whole rulebook.

### Phase 5: GUI Visualization (The Visuals)
*Goal: Make the new data types visible to the player.*

- [ ] **1. Update Character Inspector (`app/gui/panels/inspectors/character_inspector.py`)**
    - [ ] **Abilities:** Render generic values (Integer or String/Die Code).
    - [ ] **Vitals:** Render standard bars (Current/Max).
    - [ ] **Tracks (NEW):** Render Clocks (Pie charts using `ctk` canvas or simple text `(â— â— â—‹â—‹)`) or Checkboxes.
- [ ] **2. Update Inventory Inspector**
    - [ ] Group items by **Slot** (e.g., "Backpack", "Belt", "Memory Units") instead of one big list.
    - [ ] Show Capacity usage per slot (e.g., "Backpack: 15/20 lbs").

### Phase 6: Cleanup & Verification
- [ ] **1. Wipe Database:** Since the schema structure is fundamentally different, delete `ai_rpg.db` and start fresh.
- [ ] **2. Test "Kids on Bikes":** Import a rule snippet using dice as stats (d4, d20). Verify the AI extracts it as `die_code` and the Validator allows strings.
- [ ] **3. Test "Blades in the Dark":** Import a rule snippet with a "Clock". Verify the Inspector renders a track and the AI can increment it.