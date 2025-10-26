# v2 Core Workflow Implementation Plan

## Phase 1: Schemas & Validation
<!-- Relevant Docs: [System Architecture](docs/architecture.md#io), [Turn Workflow](docs/turn_workflow.md) -->
- [x] **Create `app/io/` Directory:**
  - [x] Create the `app/io/` directory for input/output schemas and validation.
- [x] **Define `TurnPlan` Schema:**
  - [x] Create `app/io/schemas.py`.
  - [x] Define a Pydantic model for `TurnPlan` that includes `thought` and `tool_calls`.
- [x] **Define `NarrativeStep` Schema:**
  - [x] In `app/io/schemas.py`, define a Pydantic model for `NarrativeStep` that includes `narrative`, `state_patch`, and `memory_intent`.

## Phase 2: Core Tool Infrastructure
<!-- Relevant Docs: [System Architecture](docs/architecture.md#Tool-Registry), [Turn Workflow](docs/turn_workflow.md) -->
- [x] **Create Directory Structure:**
  - [x] Create the `app/tools/` directory.
  - [x] Create a `app/tools/builtin/` subdirectory for the initial set of tools.
- [x] **Implement `ToolRegistry`:**
  - [x] Create `app/tools/registry.py`.
  - [x] Implement a `ToolRegistry` class that can discover, load, and execute tools from the `builtin` directory.
- [x] **Define Tool Interface:**
  - [x] Establish a base class or protocol for tools, requiring a `schema` (JSON) and a `handler` (Python function).

## Phase 2: Built-in Tools
<!-- Relevant Docs: [System Architecture](docs/architecture.md#Tool-Registry) -->
- [x] **Implement `rng.py`:**
  - [x] Create a tool for random number generation (e.g., `roll_dice`).
  - [x] Define a JSON schema for its arguments (e.g., `dice_spec`).
- [x] **Implement `math.py`:**
  - [x] Create a tool for basic math operations (e.g., `evaluate`).
  - [x] Define a JSON schema for its arguments (e.g., `expression`).

## Phase 3: Orchestrator Integration
<!-- Relevant Docs: [System Architecture](docs/architecture.md#Orchestrator), [Turn Workflow](docs/turn_workflow.md), [LLM Provider Abstraction](docs/llm_providers.md) -->
- [x] **Update `Orchestrator` for Planning:**
  - [x] Instantiate the `ToolRegistry`.
  - [x] In the main turn loop, make the first LLM call using the `TurnPlan` schema.
  - [x] Validate the LLM's response against the `TurnPlan` model.
- [x] **Handle Tool Calls:**
  - [x] Process the `tool_calls` from the validated `TurnPlan`.
  - [x] Use the `ToolRegistry` to execute the tools.
- [x] **Update `Orchestrator` for Narrative Generation:**
  - [x] Make the second LLM call using the `NarrativeStep` schema and the tool results.
  - [x] Validate the response against the `NarrativeStep` model.
  - [x] Process the `narrative`, `state_patch`, and `memory_intent` fields.

## Phase 4: UI Feedback
<!-- Relevant Docs: [UI](docs/ui.md) -->
- [x] **Display Tool Events:**
  - [x] (Optional) Add a mechanism to the UI to display when a tool is called and what the result was, for better user visibility.