## Phase 1: Prompt Template Refactoring for LLM Caching

**Goal:** Refactor `TemplateGenerationService` and its associated prompts to use a single, static system prompt for core instructions and rules, moving step-specific tasks into the user message. This optimizes for LLM providers utilizing prompt caching.

### 1. Update Prompt Templates

-   [x] **Modify `app/prompts/templates.py`:**
    -   [x] Create a new `TEMPLATE_GENERATION_SYSTEM_PROMPT` to serve as the master system prompt.
    -   [x] Rephrase existing prompts (`GENERATE_ENTITY_SCHEMA_INSTRUCTION`, `GENERATE_CORE_RULE_INSTRUCTION`, etc.) as direct, task-oriented instructions for the user message.

### 2. Refactor the Template Generation Service

-   [x] **Update `app/setup/template_generation_service.py`:**
    -   [x] Modify the `__init__` method to construct `self.static_system_prompt` by combining `TEMPLATE_GENERATION_SYSTEM_PROMPT` with the `rules_text`.
    -   [x] Update all `_generate_*` methods to pass `self.static_system_prompt` as the `system_prompt` and the specific instruction (e.g., `GENERATE_ENTITY_SCHEMA_INSTRUCTION`) within a `Message(role="user", content=...)` in the `chat_history`.
    -   [x] Ensure that context (like `attributes_context`) is correctly embedded into the `user_instruction` for relevant steps.

---

## Success Criteria

By the end of this refactor, the system should:

-   ✅ Utilize a single, static system prompt for the `TemplateGenerationService` to improve LLM caching efficiency.
-   ✅ Pass dynamic, step-specific instructions within the user message for each generation step.
-   ✅ Maintain the correct flow of context (e.g., attributes to skills) between generation steps.
-   ✅ Reduce token usage and potentially speed up template generation on LLM backends that support prompt caching.
