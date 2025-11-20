### Phase 1: Core Infrastructure & Models
*Foundational changes to support formulas and new UI styles.*

**Models (`app/models/stat_block.py`):**
- [x] Update `DerivedStatDef` to ensure it has a `formula` field (string).
- [x] Update `VitalDef` to ensure `max_formula` is explicitly defined and documented.

**Utils (`app/utils/math_engine.py` - New File):**
- [x] Create a safe formula evaluator (using `simpleeval` or restricted `eval`).
- [x] Implement `recalculate_derived_stats(entity_data, stat_template) -> updated_entity_data`.
    - Logic: Iterate through `stat_template.derived_stats`. Parse formula, look up values in `entity_data['abilities']`, calculate result, and update `entity_data['derived']`.

**Frontend Styles (`app/gui/styles.py`):**
- [x] Add a new style definition `get_dice_bubble_style` in `Theme` (e.g., high-contrast border, specific icon like ðŸŽ²).

---

### Phase 2: Setup & Rules Parsing
*Teaching the system to understand math relationships during Session Zero.*

**Prompts (`app/prompts/templates.py`):**
- [x] Add `GENERATE_DERIVED_STATS_INSTRUCTION`.
    - *Content:* Instruct the LLM to identify values calculated from other stats (e.g., "AC is 10 + Dexterity") and return the formula.
- [x] Update `GENERATE_VITALS_INSTRUCTION` to explicitly ask for **Max HP Formulas** (e.g., "10 + Constitution").

**Service (`app/setup/template_generation_service.py`):**
- [x] Update `generate_template` to include a new step for Derived Stats.
- [x] Call LLM with `GENERATE_DERIVED_STATS_INSTRUCTION`.
- [x] Parse results into `DerivedStatDef` objects and populate `stat_template.derived_stats`.
- [x] **Normalization:** Add a helper to standardize formulas (e.g., map "Dexterity" to "DEX" if the abbreviation was defined).

**Tool Schema (`app/tools/schemas.py`):**
- [x] Update `SchemaUpsertAttribute` to add an optional `formula` string field.

**Tool Handler (`app/tools/builtin/schema_upsert_attribute.py`):**
- [x] Update handler to accept `formula`.
- [x] Logic: If `formula` is present, create a `DerivedStatDef` instead of an `AbilityDef`, add to `stat_template.derived_stats`, and ensure it is removed from `abilities` if it was previously miscategorized.

---

### Phase 3: Backend Logic & Safety
*Enforcing deterministic math and triggering UI updates.*

**Backend (`app/tools/builtin/character_update.py`):**
- [x] **Safety Check:** Before applying updates, iterate through the `updates` list.
    - If a key matches a name in `stat_template.derived_stats`, **ignore it** (log a warning) or raise an error. Prevent the AI from fighting the math engine.
    - For Vitals, if `max_formula` exists, prevent direct updates to the `max` value.
- [x] **Recalculation:** At the end of the handler (before `set_entity`), call `entity = recalculate_derived_stats(entity, stat_template)`.

**Backend (`app/tools/executor.py`):**
- [x] **Reactive Events:** Modify `_post_hook` to detect state-changing tools (`character.update`, `inventory.add_item`, `inventory.remove_item`, `state.apply_patch`).
    - Emit message: `self.ui_queue.put({"type": "state_changed", "entity_type": "...", "key": "..."})`.
- [x] **Dice Events:** In `execute`, check if the tool is `rng_roll`.
    - If success, emit message *before* the standard result:
      ```python
      self.ui_queue.put({
          "type": "dice_roll",
          "spec": tool_args.get("dice") or tool_args.get("dice_spec"),
          "rolls": result["rolls"],
          "modifier": result["modifier"],
          "total": result["total"]
      })
      ```

---

### Phase 4: Frontend & UX
*Visualizing the changes.*

**Frontend (`app/gui/managers/chat_bubble_manager.py`):**
- [x] Add method `add_dice_roll(self, roll_data: dict)`.
- [x] Implement custom widget layout: Formula (top), Individual Rolls (middle), Total (bottom/bold).

**Frontend (`app/gui/managers/ui_queue_handler.py`):**
- [x] **Handle `dice_roll`:** Delegate to `self.bubble_manager.add_dice_roll`.
- [x] **Handle `state_changed`:** Trigger specific refreshes based on entity type.
    - `character` -> `self.inspectors["character"].refresh()`
    - `inventory` -> `self.inspectors["inventory"].refresh()`
    - Default -> `refresh_all`

**Frontend (`app/gui/managers/inspector_manager.py`):**
- [x] Verify `refresh()` methods are lightweight enough for frequent updates (ensure no heavy blocking DB calls).
