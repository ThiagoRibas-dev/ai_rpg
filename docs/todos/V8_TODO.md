# V8 Todo List - Initial Messages & Scaffolding

This list tracks the implementation of features for v8, focusing on improving the new game experience with initial messages and game state scaffolding.

## Phase 1: Foundation

-   [ ] **Database Schema (`db_manager.py`)**
    -   [ ] Add `initial_message` column to `prompts` table.
    -   [ ] Implement migration logic for existing databases.
    -   [ ] Update `create_prompt`, `get_all_prompts`, and `update_prompt` methods to support the new field.

-   [ ] **Models (`prompt.py`)**
    -   [ ] Add `initial_message: str` field to the `Prompt` dataclass.

-   [ ] **Scaffolding System (`setup_scaffolding.py`)**
    -   [ ] Create new file `app/core/setup_scaffolding.py`.
    -   [ ] Implement `get_initial_game_state()` to return a default game state structure (character, inventory, etc.).
    -   [ ] Define `DEFAULT_INITIAL_MESSAGE` for Session Zero.

-   [ ] **GUI - Prompt Editor (`prompt_editor_dialog.py`)**
    -   [ ] Create new file `app/gui/prompt_editor_dialog.py`.
    -   [ ] Build a dialog for creating and editing prompts with fields for Name, System Prompt, and Initial Message.
    -   [ ] Ensure the "Initial Message" field is pre-filled with the default for new prompts.

-   [ ] **GUI - Main View (`main_view.py`)**
    -   [ ] Remove the "Memory" text field from the "Advanced Context" panel.
    -   [ ] Update `new_prompt()` and `edit_prompt()` methods to use the new `PromptEditorDialog`.
    -   [ ] Modify `new_game()` to initialize the game state using the new scaffolding system.
    -   [ ] Update `new_game()` to inject the prompt's `initial_message` into the chat history when a new session starts.
    -   [ ] Update `save_context()` to no longer save the (now removed) memory field.

-   [ ] **Testing**
    -   [ ] Run `ruff check . --fix` to ensure code quality.
