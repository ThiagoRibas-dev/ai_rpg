# V3 TODO: UI Refactor and Feature Enhancement

This document outlines the development tasks for refactoring the GUI, implementing advanced context management, and adding an interactive user choice system.

---

### Phase 1: Foundational UI Refactoring (Collapsible Layout)

**Goal:** Reorganize the main view's control panel to be cleaner, more scalable, and ready for new features using a collapsible accordion-style layout.

-   [x] **Create `CollapsibleFrame` Widget:**
    -   [x] Create a new reusable widget class `CollapsibleFrame` inheriting from `ctk.CTkFrame`.
    -   [x] The widget must have a header (e.g., a `CTkButton`) with a title and an arrow icon.
    -   [x] Clicking the header should toggle the visibility of a content `CTkFrame` held within the widget.

-   [x] **Refactor `MainView` Layout:**
    -   [x] In `app/gui/main_view.py`, import and use the new `CollapsibleFrame` widget.
    -   [x] In the `_create_right_panel_widgets` method, replace existing frames with `CollapsibleFrame` instances for:
        -   "Game Sessions"
        -   "LLM Parameters"
        -   "Game State Inspector"

-   [x] **Integrate Prompt Management into Main UI:**
    -   [x] Move the content of `PromptManagerView` into a new `CollapsibleFrame` in the `MainView`.
    -   [x] The "Manage Prompts" button should now toggle this new frame instead of opening a popup.
    -   [x] Remove the `PromptManagerView` class.

---

### Phase 2: Advanced Context - Backend and Data Model

**Goal:** Extend the database schema and manager to persistently store new context elements like Memory, Author's Notes, and World Info.

-   [x] **Update Database Schema (`db_manager.py`):**
    -   [x] **Modify `sessions` Table:** Add two new `TEXT` columns: `memory` and `authors_note`.
    -   [x] **Create `world_info` Table:**
        -   `id` (INTEGER PRIMARY KEY)
        -   `prompt_id` (INTEGER, FOREIGN KEY to `prompts.id`)
        -   `keywords` (TEXT)
        -   `content` (TEXT)

-   [x] **Implement New `DBManager` Methods:**
    -   [x] Add `update_session_context(session_id, memory, authors_note)` to save session-specific context.
    -   [x] Add `get_session_context(session_id)` to retrieve session-specific context.
    -   [x] Add full CRUD (Create, Read, Update, Delete) methods for the `world_info` table, linked to a prompt ID.

---

### Phase 3: Advanced Context - Frontend and Orchestrator Integration

**Goal:** Build the UI for managing the new context elements and integrate the context assembly logic into the `Orchestrator`.

-   [x] **Create UI for Context Management (`main_view.py`):**
    -   [x] Add a new `CollapsibleFrame` titled "Advanced Context".
    -   [x] Inside, add a `CTkTextbox` for "Memory".
    -   [x] Add a `CTkTextbox` for "Author's Note".
    -   [x] Add a `CTkButton` to "Manage World Info".
    -   [x] Ensure these textboxes are populated on session load and saved on session updates.

-   [x] **Create `WorldInfoManagerView`:**
    -   [x] Create a new `WorldInfoManagerView(ctk.CTkToplevel)` class.
    -   [x] Implement a CRUD interface to manage World Info entries for the selected prompt, using the new `DBManager` methods.

-   [x] **Integrate Context Assembly in `Orchestrator`:**
    -   [x] In `plan_and_execute`, overhaul the prompt assembly logic.
    -   [x] Before calling the LLM, dynamically build the final system prompt by combining:
        1.  Memory text.
        2.  Content from any triggered World Info entries.
        3.  The core instruction from the `PLAN_TEMPLATE` or `NARRATIVE_TEMPLATE`.
        4.  Author's Note text.

---

### Phase 4: Interactive User Choices

**Goal:** Implement a system where the AI proposes a set of actions or dialogue choices for the user, who can then click a button to proceed.

-   [x] **Define `ActionChoices` Schema (`schemas.py`):**
    -   [x] Create a new Pydantic `BaseModel` named `ActionChoices`.
    -   [x] It should contain one field: `choices: List[str]`, with a description instructing the model to provide 3 concise options.

-   [x] **Update `Orchestrator` to Generate Choices:**
    -   [x] At the end of `plan_and_execute`, after displaying the narrative, add a new step.
    -   [x] Create a `CHOICE_GENERATION_TEMPLATE` to instruct the LLM.
    -   [x] Make a new call to `llm_connector.get_structured_response` using this template and the `ActionChoices` schema.
    -   [x] Pass the resulting list of choices to a new method in the `MainView`.

-   [x] **Implement Choice Buttons in `MainView`:**
    -   [x] Add a `self.choice_button_frame` (`CTkFrame`) below the user input text box.
    -   [x] Create a method `display_action_choices(self, choices: List[str])` that dynamically creates a `CTkButton` for each choice and adds it to the frame.
    -   [x] The command for each button should populate the user input box with the choice text and then trigger the send action.
    -   [x] Ensure the choice buttons are cleared at the start of each new turn.