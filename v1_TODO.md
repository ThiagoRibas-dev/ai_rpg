# v1 TODO List

## Database Setup
<!-- Relevant Docs: [System Architecture](docs/architecture.md#State-Manager), [Data Model](docs/data_model.md) -->
- [ ] **Initialize Database:**
  - [ ] Create a new module/class for database interactions (e.g., `app/database/db_manager.py`).
  - [ ] Use SQLite for the initial implementation.
  - [ ] The database should be created on first launch if it doesn't exist.
- [ ] **Define Schema:**
  - [ ] Create a `prompts` table (e.g., `id`, `name`, `content`).
  - [ ] Create a `sessions` table (e.g., `id`, `name`, `session_data`). `session_data` can be a JSON blob for now.

## Prompt Management (with Database)
<!-- Relevant Docs: [UI](docs/ui.md), [Data Model](docs/data_model.md), [System Architecture](docs/architecture.md#GUI-customtkinter) -->
- [ ] **UI for Prompt Management:**
  - [ ] Add a "Prompts" menu to the main application window.
  - [ ] Implement a "Manage Prompts" option that opens a new window.
  - [ ] The "Manage Prompts" window should list all prompts from the database.
  - [ ] Add buttons to "Create", "Edit", and "Delete" prompts in the database.
- [ ] **Backend for Prompt Loading:**
  - [ ] When starting a new game, the user can select a prompt from the list fetched from the database.
  - [ ] Ensure the selected prompt is used to initialize the game session.

## Session Persistence (with Database)
<!-- Relevant Docs: [UI](docs/ui.md), [Data Model](docs/data_model.md), [System Architecture](docs/architecture.md#State-Manager) -->
- [ ] **UI for Session Management:**
  - [ ] Add a "Session" or "Game" menu.
  - [ ] Implement a "Save Game" option that saves the current session state to the database. The user should be prompted for a name for the save.
  - [ ] Implement a "Load Game" option that lists saved games from the database for the user to choose from.
- [ ] **Backend for Session State:**
  - [ ] Define a clear data structure for the session state (e.g., chat history, character stats, world state).
  - [ ] Implement serialization logic to convert the session state to a JSON blob before saving to the database.
  - [ ] Implement deserialization logic to load a session from the database and restore the application state.