## Phase 1: Service & Prompt Refactoring

**Goal:** Rearchitect the template generation logic from a single function into a stateful service that orchestrates multiple, focused LLM calls.

### Create `TemplateGenerationService`

-   [x] **Create `app/setup/template_generation_service.py`:**
    -   [x] Define a new class `TemplateGenerationService` to replace the existing `TemplateGenerator`.
    -   [x] The `__init__` method should accept `llm: LLMConnector`, `rules_text: str`, and an optional `status_callback: Callable[[str], None]` for GUI updates.
    -   [x] Create a main public method `generate_template()` that will orchestrate the entire pipeline.
    -   [x] Create private methods for each step of the pipeline (e.g., `_generate_entity_schemas`, `_generate_core_rule`, etc.).

### Decompose Prompts

-   [x] **Refactor `app/prompts/templates.py`:**
    -   [x] Remove the large, all-in-one `RULES_ANALYSIS_PROMPT`.
    -   [x] Create new, specific system prompts for each generation step:
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

-   [x] **Implement `_generate_entity_schemas()`:**
    -   [x] Call the LLM with `GENERATE_ENTITY_SCHEMA_PROMPT` and the raw rules text.
    -   [x] The expected output schema should be `EntitySchema`.
    -   [x] Return a valid `EntitySchema` object, or an empty one on failure.

-   [x] **Implement `_generate_core_rule()`:**
    -   [x] Construct a new prompt that includes the raw rules text *and* the JSON of the attributes generated in the previous step.
    -   [x] Call the LLM with `GENERATE_CORE_RULE_PROMPT`.
    -   [x] The expected output schema is `RuleSchema`.
    -   [x] Return a `RuleSchema` object or `None` on failure.

-   [x] **Implement `_generate_action_economy()`:**
    -   [x] Call the LLM with `GENERATE_ACTION_ECONOMY_PROMPT`.
    -   [x] The expected output schema is `ActionEconomyDefinition`.
    -   [x] Return an `ActionEconomyDefinition` object or `None` on failure.

-   [x] **Implement `_generate_skills()`:**
    -   [x] Construct a prompt including the raw rules and the generated attributes JSON.
    -   [x] Call the LLM with `GENERATE_SKILLS_PROMPT`.
    -   [x] The expected output schema is `List[SkillDefinition]`.
    -   [x] Return a list of `SkillDefinition` objects, or an empty list on failure.

-   [x] **Implement `_generate_conditions()`:**
    -   [x] Call the LLM with `GENERATE_CONDITIONS_PROMPT`.
    -   [x] The expected output schema is `List[ConditionDefinition]`.

-   [x] **Implement `_generate_classes()` and `_generate_races()`:**
    -   [x] Construct prompts including context from attributes and skills.
    -   [x] Call the LLM with their respective prompts and schemas (`List[ClassDefinition]`, `List[RaceDefinition]`).

### Assemble Final Template

-   [x] **Finalize `generate_template()` method:**
    -   [x] Call each private generation method in the correct order.
    -   [x] Use the `status_callback` between each step to report progress (e.g., `self._update_status("Defining Core Rules...")`).
    -   [x] Assemble the results from all steps into a single `GameTemplate` Pydantic object.
    -   [x] Return the final result as a dictionary using `.model_dump()`.

---

## Phase 3: GUI Integration

**Goal:** Update the `PromptDialog` to use the new service and provide real-time feedback to the user.

### Update `PromptDialog`

-   [x] **Modify `_generate_template_background()` in `prompt_dialog.py`:**
    -   [x] Replace the instantiation of the old `TemplateGenerator` with the new `TemplateGenerationService`.
    -   [x] Create a new method `_update_generation_status(self, message: str)` in the dialog that is thread-safe for updating the `self.generate_status` label.
    -   [x] Pass a lambda function to the `TemplateGenerationService` constructor for the `status_callback` parameter, which calls `self.after(0, self._update_generation_status, message)`.

-   [x] **Enhance User Feedback:**
    -   [x] Ensure the "Generate" button is disabled during the entire multi-step process.
    -   [x] The `generate_status` label should now show a sequence of updates: "Analyzing Attributes...", "Defining Skills...", etc.
    -   [x] Upon completion, the final status ("✅ Generated X properties") should be displayed as before.
    -   [x] Error handling should clearly report if a specific step failed.

---

## Success Criteria

By the end of this refactor, the system should:

-   ✅ Generate a `GameTemplate` by calling the LLM multiple times for different sub-sections of the schema.
-   ✅ Pass the output of early generation steps (like Attributes) as context to later steps (like Skills).
-   ✅ Provide step-by-step progress updates to the user in the `PromptDialog` GUI.
-   ✅ Produce more detailed, accurate, and reliable game system templates compared to the single-shot method.
-   ✅ Isolate generation failures to a specific step, making debugging easier.