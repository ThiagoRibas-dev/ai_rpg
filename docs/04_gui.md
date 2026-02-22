# GUI

The user interface is built with NiceGUI.

## Layout
- **Header**: Global controls, session indicators, and Zen Mode toggle.
- **Left Drawer**: Live State Inspectors (Characters, Organizations, Locations, etc. updating based on manifest).
- **Center Area**: Main chat view for interacting with the orchestrator, and session selection.
- **Right Drawer**: Tabbed view for Game Scene overview, Lorebook management, and chat configurations.
- **Dialogs**: A large mapping overlay.

## Technical Details
- Built entirely using NiceGUI's reactive web capabilities.
- Backend async operations and LLM generation run in thread pools.
- Thread-safe communication uses a `NiceGUIBridge` queue system to trigger UI updates without blocking the interface.
