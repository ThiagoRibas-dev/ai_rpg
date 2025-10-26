# v1 TODO List

## Database Setup
<!-- Relevant Docs: [System Architecture](docs/architecture.md#State-Manager), [Data Model](docs/data_model.md) -->
- [x] **Initialize Database:**
  - [x] Create a new module/class for database interactions (e.g., `app/database/db_manager.py`).
  - [x] Use SQLite for the initial implementation.
  - [x] The database should be created on first launch if it doesn't exist.
- [x] **Define Schema:**
  - [x] Create a `prompts` table (e.g., `id`, `name`, `content`).
  - [x] Create a `sessions` table (e.g., `id`, `name`, `session_data`). `session_data` can be a JSON blob for now.

## Prompt Management (with Database)
<!-- Relevant Docs: [UI](docs/ui.md), [Data Model](docs/data_model.md), [System Architecture](docs/architecture.md#GUI-customtkinter) -->
- [x] **UI for Prompt Management:**
  - [x] Add a "Prompts" menu to the main application window.
  - [x] Implement a "Manage Prompts" option that opens a new window.
  - [x] The "Manage Prompts" window should list all prompts from the database.
  - [x] Add buttons to "Create", "Edit", and "Delete" prompts in the database.
- [x] **Backend for Prompt Loading:**
  - [x] When starting a new game, the user can select a prompt from the list fetched from the database.
  - [x] Ensure the selected prompt is used to initialize the game session.

## Session Persistence (with Database)
<!-- Relevant Docs: [UI](docs/ui.md), [Data Model](docs/data_model.md), [System Architecture](docs/architecture.md#State-Manager) -->
- [x] **UI for Session Management:**
  - [x] Add a "Session" or "Game" menu.
  - [x] Implement a "Save Game" option that saves the current session state to the database. The user should be prompted for a name for the save.
  - [x] Implement a "Load Game" option that lists saved games from the database for the user to choose from.
- [x] **Backend for Session State:**
  - [x] Define a clear data structure for the session state (e.g., chat history, character stats, world state).
  - [x] Implement serialization logic to convert the session state to a JSON blob before saving to the database.
  - [x] Implement deserialization logic to load a session from the database and restore the application state.