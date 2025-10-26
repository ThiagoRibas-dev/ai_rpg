# GUI

The user interface is built with customtkinter.

## Layout
- **Left panel**: Session selector; Provider selector (Gemini/OpenAI-compatible), temperature/top-p reset, fast/creative toggle.
- **Main center**: Chat/Transcript with token-streaming; inline tool-events (dice rolls, patch summaries).
- **Right panel (State Inspector)**: tabs for Characters, Locations, Inventory, Quests, Lore, Memory queue (proposals pending approval).
- **Bottom**: AI suggestions, free text input box.

## Technical Details
- The GUI runs in the main thread.
- Model interactions and other long-running tasks are executed in a background worker thread to keep the UI responsive.
- Communication between the background thread and the UI thread is handled via a queue system to ensure thread safety.
