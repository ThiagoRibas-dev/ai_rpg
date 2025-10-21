# UI (customtkinter) Layout

The user interface is designed with a two-panel layout, inspired by interfaces like `mikupad`, to provide a clear separation between the narrative and the controls.

- **Main Panel (Left/Center)**: This is the primary interaction area.
  - **Chat/Transcript**: Displays the game's narrative, dialogue, and events in a scrollable text box.
  - **User Input**: A multi-line text box for the player to enter their actions and dialogue.
  - **Buttons**: "Send" and "Stop/Cancel" buttons for submitting input or interrupting the AI's response. The "Send" button is disabled until a game session is selected.

- **Control Panel (Right)**: A sidebar with collapsible sections for managing the game and its parameters.
  - **Prompt Management**:
    - A listbox to display all available system prompts.
    - Selecting a prompt from this list filters the "Game Sessions" list below.
    - A button to open the prompt management window to create, edit, or delete prompts.
  - **Game Session Management**:
    - A list of saved game sessions for the currently selected prompt.
    - Selecting a session from this list loads the game.
    - A "New Game" button that automatically creates a new session with a timestamp-based name (e.g., `{yyyy-mm-dd_hh:mm}_{Prompt_Name}`).
    - The game state is saved automatically after each AI response.
  - **LLM Parameters**:
    - A dropdown to select the LLM provider (e.g., Gemini, OpenAI).
    - Sliders to adjust parameters like `temperature` and `top_p`.
  - **Game State Inspector**:
    - A tabbed view to inspect the current game state, including tabs for "Characters", "Inventory", "Quests", and "Lore".