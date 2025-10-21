# v2 Core Workflow Implementation Plan

## Phase 1: Schemas & Validation
<!-- Relevant Docs: [System Architecture](docs/architecture.md#io), [Turn Workflow](docs/turn_workflow.md) -->
- [ ] **Create `app/io/` Directory:**
  - [ ] Create the `app/io/` directory for input/output schemas and validation.
- [ ] **Define `TurnPlan` Schema:**
  - [ ] Create `app/io/schemas.py`.
  - [ ] Define a Pydantic model for `TurnPlan` that includes `thought` and `tool_calls`.
- [ ] **Define `NarrativeStep` Schema:**
  - [ ] In `app/io/schemas.py`, define a Pydantic model for `NarrativeStep` that includes `narrative`, `state_patch`, and `memory_intent`.

## Phase 2: Core Tool Infrastructure
<!-- Relevant Docs: [System Architecture](docs/architecture.md#Tool-Registry), [Turn Workflow](docs/turn_workflow.md) -->
- [ ] **Create Directory Structure:**
  - [ ] Create the `app/tools/` directory.
  - [ ] Create a `app/tools/builtin/` subdirectory for the initial set of tools.
- [ ] **Implement `ToolRegistry`:**
  - [ ] Create `app/tools/registry.py`.
  - [ ] Implement a `ToolRegistry` class that can discover, load, and execute tools from the `builtin` directory.
- [ ] **Define Tool Interface:**
  - [ ] Establish a base class or protocol for tools, requiring a `schema` (JSON) and a `handler` (Python function).

## Phase 2: Built-in Tools
<!-- Relevant Docs: [System Architecture](docs/architecture.md#Tool-Registry) -->
- [ ] **Implement `rng.py`:**
  - [ ] Create a tool for random number generation (e.g., `roll_dice`).
  - [ ] Define a JSON schema for its arguments (e.g., `dice_spec`).
- [ ] **Implement `math.py`:**
  - [ ] Create a tool for basic math operations (e.g., `evaluate`).
  - [ ] Define a JSON schema for its arguments (e.g., `expression`).

## Phase 3: Orchestrator Integration
<!-- Relevant Docs: [System Architecture](docs/architecture.md#Orchestrator), [Turn Workflow](docs/turn_workflow.md), [LLM Provider Abstraction](docs/llm_providers.md) -->
- [ ] **Update `Orchestrator` for Planning:**
  - [ ] Instantiate the `ToolRegistry`.
  - [ ] In the main turn loop, make the first LLM call using the `TurnPlan` schema.
  - [ ] Validate the LLM's response against the `TurnPlan` model.
- [ ] **Handle Tool Calls:**
  - [ ] Process the `tool_calls` from the validated `TurnPlan`.
  - [ ] Use the `ToolRegistry` to execute the tools.
- [ ] **Update `Orchestrator` for Narrative Generation:**
  - [ ] Make the second LLM call using the `NarrativeStep` schema and the tool results.
  - [ ] Validate the response against the `NarrativeStep` model.
  - [ ] Process the `narrative`, `state_patch`, and `memory_intent` fields.

## Phase 4: UI Feedback
<!-- Relevant Docs: [UI](docs/ui.md) -->
- [ ] **Display Tool Events:**
  - [ ] (Optional) Add a mechanism to the UI to display when a tool is called and what the result was, for better user visibility.