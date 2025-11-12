# V9 TODO List

- [x] **Database Schema - Add Template Storage**
    *   [x] `app/database/db_manager.py`: Added `rules_document` and `template_manifest` columns to the `prompts` table and updated `create_prompt` to handle them.
    *   [x] `app/database/repositories/prompt_repository.py`: Updated `create`, `get_all`, `get_by_id`, and `update` methods to manage the new `rules_document` and `template_manifest` fields.

- [x] **Prompt Model Update**
    *   [x] `app/models/prompt.py`: Added `rules_document` and `template_manifest` fields to the `Prompt` dataclass.

- [x] **Game Template Models**
    *   [x] `app/models/game_template.py`: Created a new file defining Pydantic models for various game system components (attributes, resources, skills, action economy, etc.) and a `GameTemplate` to encapsulate them.

- [x] **Template Generator Service**
    *   [x] `app/core/template_generator.py`: Created a new file with a `TemplateGenerator` class to extract structured game mechanics from rules documents using AI, and a `validate_descriptions` function for quality control.

- [x] **Prompt Dialog UI Enhancements**
    *   [x] `app/gui/panels/prompt_dialog.py`: Added UI elements for rules document input, a "Generate Template" button, and a template preview. Implemented background processing for AI generation and updated `_load_existing_data` and `_on_save` to manage the new fields.

- [x] **Prompt Manager Update**
    *   [x] `app/gui/managers/prompt_manager.py`: Updated `new_prompt` and `edit_prompt` methods to correctly handle the new `rules_document` and `template_manifest` fields from the dialog.

- [x] **Session Template Inheritance**
    *   [x] `app/gui/managers/session_manager.py`: Added `_apply_template_to_session` to copy template manifests into a session's setup data. Modified `new_game` to automatically apply the selected prompt's template to a new session.

- [x] **Lean System Prompt Builder**
    *   [x] `app/core/llm/prompts.py`: Added `build_lean_schema_reference` to generate a concise summary of game mechanics for inclusion in the system prompt.

- [x] **Orchestrator Integration**
    *   [x] `app/core/orchestrator.py`: Integrated `SetupManifest` and `build_lean_schema_reference` into `_background_execute` to build and pass a lean schema reference to the context builder.
    *   [x] `app/core/context/context_builder.py`: Modified `build_static_system_instruction` to accept and include the `schema_ref` in the system prompt.

- [x] **Schema Query Tool**
    *   [x] `app/tools/schemas.py`: Added the `SchemaQuery` Pydantic model for querying game mechanics.
    *   [x] `app/tools/builtin/schema_query.py`: Created a new file with the `handler` function for the `schema.query` tool, enabling on-demand lookup of detailed game mechanics.

- [x] **Tool Availability Update**
    *   [x] `app/core/orchestrator.py`: Added `"schema.query"` to the `setup_tool_names` list, making it available during the SETUP game mode.