# AI RPG Prompt Caching Optimization

This document tracks the implementation of prompt caching optimization and workflow improvements for the AI RPG, focusing on performance, consistency, and user experience.

## Core Architecture Changes

### Context Management
- [x] **`app/core/context/context_builder.py`**: Complete refactor to separate static and dynamic content
  - [x] Implement `build_static_system_instruction()` for cacheable prompt components
  - [x] Implement `build_dynamic_context()` for per-turn changing content
  - [x] Update `get_truncated_history()` to exclude system messages (now stored separately)
  - [x] Remove old `assemble()` method (no longer needed)

### Session Model
- [x] **`app/models/session.py`**: Refactor to store system prompt separately from chat history
  - [x] Add `system_prompt` attribute (not in history array)
  - [x] Update `add_message()` to handle system messages separately
  - [x] Add `get_system_prompt()` getter method
  - [x] Update `to_json()` and `from_json()` to serialize/deserialize system_prompt
  - [x] Change `history` to start empty (no system message at index 0)

### LLM Services with Response Prefilling

- [x] **`app/core/llm/planner_service.py`**: Update to use static instruction + prefill
  - [x] Change method signature to accept `system_instruction`, `phase_template`, `dynamic_context`
  - [x] Build assistant prefill combining phase instructions and dynamic context
  - [x] Append prefill as assistant message to chat history
  - [x] Pass only static instruction to LLM connector

- [x] **`app/core/llm/narrator_service.py`**: Update to use static instruction + prefill with prior phase context
  - [x] Change method signature to accept `plan_thought` and `tool_results` from prior phases
  - [x] Build prefill including planning context, tool results, phase template, and dynamic context
  - [x] Reuse same static instruction as planning phase (cache preserved)

- [x] **`app/core/llm/choices_service.py`**: Update to use static instruction + prefill with narrative context
  - [x] Change method signature to accept `narrative_text` from prior phase
  - [x] Build prefill including narrative context and phase template
  - [x] Reuse same static instruction (cache preserved)

### Orchestrator Workflow

- [x] **`app/core/orchestrator.py`**: Major refactor for cache-optimized multi-phase turns
  - [x] Build static instruction once per session/mode (with caching logic)
  - [x] Build chat history once before all phases (no updates between phases)
  - [x] Rebuild dynamic context after tool execution (state may have changed)
  - [x] Pass prior phase outputs to subsequent phases via prefill
  - [x] Update chat history only after ALL phases complete
  - [x] Add cache invalidation on mode changes
  - [x] Add game mode update UI notification

### LLM Connectors

- [x] **`app/llm/openai_connector.py`**: Fix to return validated Pydantic instances
  - [x] Replace `json.loads()` with `output_schema.model_validate_json()`
  - [x] Add error handling for ValidationError and JSONDecodeError
  - [x] Add logging for debugging failed validations

- [x] **`app/llm/gemini_connector.py`**: Already returns validated instances via `response.parsed`
  - [x] Verify compatibility with new workflow (no changes needed)

## Prompt Updates

- [x] **`app/core/llm/prompts.py`**: Update all phase templates to first-person perspective
  - [x] `PLAN_TEMPLATE`: "I am now in the planning phase. My role is to..."
  - [x] `NARRATIVE_TEMPLATE`: "I am now in the narrative phase. My role is to..."
  - [x] `CHOICE_GENERATION_TEMPLATE`: "I am now generating 3-5 action choices..."
  - [x] `SESSION_ZERO_TEMPLATE`: "I am in the system definition phase. My role is to..."
  - [x] Remove formatting placeholders (now handled in orchestrator via prefill)
  - [x] Add explicit notes about tool_calls validation (never use empty objects)

## Tool Validation & Error Handling

- [x] **`app/core/dynamic_schema.py`**: Add validators to filter invalid tool calls
  - [x] Create `validate_tool_calls` function to filter out empty objects and missing names
  - [x] Integrate validator into dynamically created TurnPlan model
  - [x] Add logging for filtered tool calls
  - [x] Handle edge case of no available tools (empty list validation)

- [x] **`app/core/tools/executor.py`**: Improve error handling for invalid tool instances
  - [x] Add defensive checks for raw `BaseModel` instances
  - [x] Verify `name` attribute exists before accessing
  - [x] Add try-catch for `model_dump()` failures
  - [x] Return detailed error results for invalid tool calls
  - [x] Improve logging to avoid errors when logging failed calls

## GUI Enhancements

- [x] **`app/gui/main_view.py`**: Add game mode indicator to header
  - [x] Add `game_mode_label` widget centered in game_time_frame
  - [x] Implement `_get_mode_display()` helper method for mode-specific text/colors
  - [x] Update `on_session_select()` to set game mode when loading session
  - [x] Add `update_game_mode` case to `_handle_ui_message()`
  - [x] Use emojis for visual indicators (📋 SETUP, ⚔️ GAMEPLAY)

- [x] **`app/gui/styles.py`**: (Optional) Add game mode colors
  - [x] Add `mode_setup` and `mode_gameplay` color definitions

## Tool Schema Refactor and Prompt Simplification

- [x] **Enriched Tool Schemas (`app/tools/schemas.py`)**
    - Added detailed usage guidance, examples, and best practices directly into each tool's Pydantic model docstring and field descriptions.
- [x] **Removed `TOOL_USAGE_GUIDELINES` (`app/core/llm/prompts.py`)**
    - Eliminated the separate `TOOL_USAGE_GUIDELINES` section from the prompt templates.
- [x] **Simplified Static Instruction (`app/core/context/context_builder.py`)**
    - Updated the `build_static_system_instruction` method to no longer include the `TOOL_USAGE_GUIDELINES` section, resulting in a cleaner prompt structure.
- [x] **Tighter Phase Templates (`app/core/orchestrator.py`)**
    - Ensured `SESSION_ZERO_TEMPLATE` is correctly imported, aligning with the simplified prompt structure and removing any references to the deleted guidelines.
