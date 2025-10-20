# AI-RPG: A Dynamic, LLM-Powered RPG Engine

## High-Level Spec
An advanced, text-based RPG engine powered by Large Language Models (LLMs). The engine will dynamically generate narrative, manage game state, and respond to player actions by intelligently retrieving and managing context. The core design focuses on a modular architecture that separates state management, decision logic, and LLM interaction, allowing for support of multiple LLM backends like Gemini and OpenAI.

## Detailed Specification

This project is documented across several files to keep the information organized and easy to navigate.

- **[System Architecture](docs/architecture.md)**: A high-level overview of the system's components and their interactions, including the folder structure.
- **[Data Model](docs/data_model.md)**: Details on the database schema and data structures used to store game state and session information.
- **[User Interface (UI)](docs/ui.md)**: A description of the customtkinter layout and user-facing components.
- **[LLM Provider Abstraction](docs/llm_providers.md)**: Information on how the application interfaces with different Large Language Models.
- **[Turn Workflow](docs/turn_workflow.md)**: A step-by-step breakdown of how the application processes a user's turn.
- **[Roadmap](docs/roadmap.md)**: The development plan and future features.

## TODOs
- **[V0 TODO](v0_TODO.md)**: A step by step TODO for the initial MVP implementation (completed).
- **[V1 TODO](v1_TODO.md)**: A step by step TODO for the v1 implementation.

## Development Workflow
  - Examination
  - Planning (what, where, how, why), including details of implementation
  - Refining (break into components, detail, consider possibilities, brainstorm)
  - Iteration
  - Presenting the detailed plan with code snippet examples
  - Request and wait for permission to Execute/Implement the plan
  - Write temporary TODO file to keep track of the implementation
  - Execution/implementation (reading files, creating/editing/deleting, etc) while updating the temporary TODO
  - Check the work for missing or imcomplete implementations
  - Run ruff to check for errors
  - Run the game to check for errors
  - Summarize changes
  - Ask for next step
Always ponder and consider the possible downstream effects