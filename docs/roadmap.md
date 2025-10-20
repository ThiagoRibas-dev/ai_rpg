# Roadmap

- **v0 (MVP)**
  - Basic GUI with streaming chat interface.
  - Pluggable LLM backends (Gemini and OpenAI-compatible).
  - Simple session management (in-memory).
  - Ability to load initial adventure prompts from files.

- **v1**
  - **Prompt Management:** Introduce a menu to create and load adventure prompts.
  - **Session Persistence:** Save and load session state to files/database.

- **v2**
  - **Tool System:** Implement a basic tool system for deterministic actions (e.g., dice rolls, maths).
  - **State Management:** Introduce a robust state management system (e.g., SQLite) for characters, inventory, and world state.
  - **RAG:** Integrate a simple RAG system for world lore and long-term memory.
  - **UI Enhancements:** Add a state inspector panel to the UI.

- **v3**
  - **Advanced Tools:** Expand the tool system with more complex actions.
  - **Advanced RAG:** Implement hybrid search and more sophisticated context retrieval.
  - **Multi-agent System:** Explore multi-agent setups (e.g., narrator vs. rules engine).
  - **Plugin System:** Develop a plugin system for custom tools and content.