## Phase 1: Service & Prompt Refactoring

**Goal:** Rearchitect the template generation logic from a single function into a stateful service that orchestrates multiple, focused LLM calls.

### Create `TemplateGenerationService`

-   [ ] **Create `app/setup/template_generation_service.py`:**
    -   [ ] Define a new class `TemplateGenerationService` to replace the existing `TemplateGenerator`.
    -   [ ] The `__init__` method should accept `llm: LLMConnector`, `rules_text: str`, and an optional `status_callback: Callable[[str], None]` for GUI updates.
    -   [ ] Create a main public method `generate_template()` that will orchestrate the entire pipeline.
    -   [ ] Create private methods for each step of the pipeline (e.g., `_generate_entity_schemas`, `_generate_core_rule`, etc.).

### Decompose Prompts

-   [ ] **Refactor `app/prompts/templates.py`:**
    -   [ ] Remove the large, all-in-one `RULES_ANALYSIS_PROMPT`.
    -   [ ] Create new, specific system prompts for each generation step:
        -   `GENERATE_ENTITY_SCHEMA_PROMPT`: Focuses only on Attributes (STR, DEX) and Resources (HP, Mana). Must enforce the "concise description" rule.
        -   `GENERATE_CORE_RULE_PROMPT`: Focuses on extracting the primary dice resolution mechanic. Will receive generated attributes as context.
        -   `GENERATE_ACTION_ECONOMY_PROMPT`: Focuses on turn structure (Action Points, Standard/Move/Bonus, etc.).
        -   `GENERATE_SKILLS_PROMPT`: Focuses on skills. Will receive generated attributes as context to correctly set `linked_attribute`.
        -   `GENERATE_CONDITIONS_PROMPT`: Focuses on status effects.
        -   `GENERATE_CLASSES_PROMPT`: Focuses on character classes. Will receive attributes and skills as context.
        -   `GENERATE_RACES_PROMPT`: Focuses on character races/species.

---

## Phase 2: Implement the Generation Pipeline

**Goal:** Build out the sequential logic within `TemplateGenerationService`, ensuring the output of each step is used as context for subsequent steps.

### Implement Pipeline Steps

-   [ ] **Implement `_generate_entity_schemas()`:**
    -   [ ] Call the LLM with `GENERATE_ENTITY_SCHEMA_PROMPT` and the raw rules text.
    -   [ ] The expected output schema should be `EntitySchema`.
    -   [ ] Return a valid `EntitySchema` object, or an empty one on failure.

-   [ ] **Implement `_generate_core_rule()`:**
    -   [ ] Construct a new prompt that includes the raw rules text *and* the JSON of the attributes generated in the previous step.
    -   [ ] Call the LLM with `GENERATE_CORE_RULE_PROMPT`.
    -   [ ] The expected output schema is `RuleSchema`.
    -   [ ] Return a `RuleSchema` object or `None` on failure.

-   [ ] **Implement `_generate_action_economy()`:**
    -   [ ] Call the LLM with `GENERATE_ACTION_ECONOMY_PROMPT`.
    -   [ ] The expected output schema is `ActionEconomyDefinition`.
    -   [ ] Return an `ActionEconomyDefinition` object or `None` on failure.

-   [ ] **Implement `_generate_skills()`:**
    -   [ ] Construct a prompt including the raw rules and the generated attributes JSON.
    -   [ ] Call the LLM with `GENERATE_SKILLS_PROMPT`.
    -   [ ] The expected output schema is `List[SkillDefinition]`.
    -   [ ] Return a list of `SkillDefinition` objects, or an empty list on failure.

-   [ ] **Implement `_generate_conditions()`:**
    -   [ ] Call the LLM with `GENERATE_CONDITIONS_PROMPT`.
    -   [ ] The expected output schema is `List[ConditionDefinition]`.

-   [ ] **Implement `_generate_classes()` and `_generate_races()`:**
    -   [ ] Construct prompts including context from attributes and skills.
    -   [ ] Call the LLM with their respective prompts and schemas (`List[ClassDefinition]`, `List[RaceDefinition]`).

### Assemble Final Template

-   [ ] **Finalize `generate_template()` method:**
    -   [ ] Call each private generation method in the correct order.
    -   [ ] Use the `status_callback` between each step to report progress (e.g., `self._update_status("Defining Core Rules...")`).
    -   [ ] Assemble the results from all steps into a single `GameTemplate` Pydantic object.
    -   [ ] Return the final result as a dictionary using `.model_dump()`.

---

## Phase 3: GUI Integration

**Goal:** Update the `PromptDialog` to use the new service and provide real-time feedback to the user.

### Update `PromptDialog`

-   [ ] **Modify `_generate_template_background()` in `prompt_dialog.py`:**
    -   [ ] Replace the instantiation of the old `TemplateGenerator` with the new `TemplateGenerationService`.
    -   [ ] Create a new method `_update_generation_status(self, message: str)` in the dialog that is thread-safe for updating the `self.generate_status` label.
    -   [ ] Pass a lambda function to the `TemplateGenerationService` constructor for the `status_callback` parameter, which calls `self.after(0, self._update_generation_status, message)`.

-   [ ] **Enhance User Feedback:**
    -   [ ] Ensure the "Generate" button is disabled during the entire multi-step process.
    -   [ ] The `generate_status` label should now show a sequence of updates: "Analyzing Attributes...", "Defining Skills...", etc.
    -   [ ] Upon completion, the final status ("✅ Generated X properties") should be displayed as before.
    -   [ ] Error handling should clearly report if a specific step failed.

---

## Success Criteria

By the end of this refactor, the system should:

-   ✅ Generate a `GameTemplate` by calling the LLM multiple times for different sub-sections of the schema.
-   ✅ Pass the output of early generation steps (like Attributes) as context to later steps (like Skills).
-   ✅ Provide step-by-step progress updates to the user in the `PromptDialog` GUI.
-   ✅ Produce more detailed, accurate, and reliable game system templates compared to the single-shot method.
-   ✅ Isolate generation failures to a specific step, making debugging easier.