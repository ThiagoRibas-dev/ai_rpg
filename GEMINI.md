# Gemini-Aided Development Guide

This file serves as a central rules and filedocument index and guide for AI-aided development within the AI-RPG project. It outlines the overall development workflow, provides a high-level specification of the project, and indexes key documentation files and TODO lists to facilitate efficient development.

# Development Workflow

This workflow is designed to leverage AI agent capabilities while maintaining project-specific quality standards and clear human oversight.
The development environment is Windows and the Shell is Powershell.

1.  **Task Ingestion & Contextual Analysis:** Perform an initial examination of the request and analyze relevant project context (e.g., file structure, existing documentation, previous TODOs).
2.  **Strategic Plan Formulation & Presentation:** Formulate a detailed step-by-step plan, including the 'what, where, how, why' of the implementation, breaking it into components, and considering potential downstream effects. Include code snippet examples where appropriate, then present this detailed plan to the user.
3.  **User Approval & Task Kick-off:** Request and wait for user permission to execute the plan. Upon approval, create a temporary TODO file (e.g., `vX_TODO.md`) to track the implementation steps.
4.  **Iterative Execution & Progress Tracking:** Execute the plan, performing implementation tasks (reading files, creating/editing/deleting code, etc.) in an iterative manner. Continuously update the temporary TODO file to reflect progress, marking completed steps and adding new ones as needed.
5.  **Automated Quality & Integrity Checks:** Perform project-specific quality checks: Check the work for missing or incomplete implementations. Run `ruff check --fix .` to ensure code quality and adherence to style guidelines. Run the game or relevant tests to check for functional errors.
6.  **Finalization, Documentation & Handoff:** Summarize the changes made, update relevant project files (e.g., indexes, main TODOs, `GEMINI.md`), and provide a concise summary of the completed work. Ask for the next step, signaling readiness for a new task or further instructions.

## High-Level Specification

An advanced, text-based RPG engine powered by Large Language Models (LLMs). The engine will dynamically generate narrative, manage game state, and respond to player actions by intelligently retrieving and managing context. The core design focuses on a modular architecture that separates state management, decision logic, and LLM interaction, allowing for support of multiple LLM backends like Gemini and OpenAI.

## Detailed Specification & Documentation

This project is documented across several files to keep the information organized and easy to navigate.

- **[System Architecture](docs/architecture.md)**
- **[Data Model](docs/data_model.md)**
- **[User Interface (UI)](docs/ui.md)**
- **[LLM Provider Abstraction](docs/llm_providers.md)**
- **[Turn Workflow](docs/turn_workflow.md)**
- **[Roadmap](docs/roadmap.md)**

## Project TODOs

- **[V0 TODO](v0_TODO.md)**
- **[V1 TODO](v1_TODO.md)**
- **[V1.5 TODO](v1.5_TODO.md)**
- **[V1.6 TODO](v1.6_TODO.md)**
- **[V1.7 TODO](v1.7_TODO.md)**
- **[V2 TODO](v2_TODO.md)**
- **[V2.1 TODO](v2.1_TODO.md)**

## Notes

**Planning:** Before making any changes, we will perform an iterative planning step, laying out a detailed step-by-step implementation plan (what, where, how, why). Only once the plan has been accepted, we will execute the plan and edit the files in question.

**Editing Files:** Avoid trying to edit whole files at once if possible. Edit specific, directed, targeted snippets at a time, always planning the whole chain of edits beforehand. Be aware of replacing snippets that exist in multiple parts of a given file. Files should be kept as relatively small. If a file is becoming too large (500+ lines) then split the file into two or more.

**Ruff Linter:** During Execution, after performing a batch of changes, always run `ruff check . --fix` to ensure things are in order.

**Logging:** All code will contain tracking logs that output to the console so that errors are easier to debug.

**Gemini API Schema Limitations:** A key architectural constraint is that the Google Gemini API's schema validation for structured JSON output is very strict. It does not support free-form dictionaries (e.g., `Dict[str, int]`) because they translate to a JSON schema with `"type": "object"` but no defined `"properties"`, which the API rejects. Furthermore, the `additionalProperties` field, a common way to define dictionaries in JSON Schema, is also not supported.
Some notes from the `types.py` file from google's genai library:
```
    response_schema: Optional[SchemaUnion] = Field(
        default=None,
        description="""The `Schema` object allows the definition of input and output data types.
        These types can be objects, but also primitives and arrays.
        Represents a select subset of an [OpenAPI 3.0 schema
        object](https://spec.openapis.org/oas/v3.0.3#schema).
        If set, a compatible response_mime_type must also be set.
        Compatible mimetypes: `application/json`: Schema for JSON response.
        """,
    )
    response_json_schema: Optional[Any] = Field(
        default=None,
        description="""Optional. Output schema of the generated response.
        This is an alternative to `response_schema` that accepts [JSON
        Schema](https://json-schema.org/). If set, `response_schema` must be
        omitted, but `response_mime_type` is required. While the full JSON Schema
        may be sent, not all features are supported. Specifically, only the
        following properties are supported: - `$id` - `$defs` - `$ref` - `$anchor`
        - `type` - `format` - `title` - `description` - `enum` (for strings and
        numbers) - `items` - `prefixItems` - `minItems` - `maxItems` - `minimum` -
        `maximum` - `anyOf` - `oneOf` (interpreted the same as `anyOf`) -
        `properties` - `additionalProperties` - `required` The non-standard
        `propertyOrdering` property may also be set. Cyclic references are
        unrolled to a limited degree and, as such, may only be used within
        non-required properties. (Nullable properties are not sufficient.) If
        `$ref` is set on a sub-schema, no other properties, except for than those
        starting as a `$`, may be set.""",
    )
  ```