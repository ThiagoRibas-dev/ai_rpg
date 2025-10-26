# v0 MVP Implementation Plan

This plan focuses on the "core narrative loop."

- [x] **1. Foundational Setup:** Create the core directory structure (`app/core`, `app/gui`, `app/models`) and basic configuration for API keys.
- [x] **2. LLM Abstraction Layer:** Implement the base `LLMConnector` and create concrete implementations for Gemini and OpenAI-compatible APIs.
- [x] **3. Core Logic & Session Management:** Develop simple classes for managing conversation history and saving/loading sessions to local files (e.g., JSON).
- [x] **4. Basic UI Implementation:** Build the main application window using customtkinter, including a transcript display, a user input field, and a send button.
- [x] **5. Orchestration:** Create a central orchestrator to connect the UI, session management, and the LLM abstraction layer, managing the flow of a single turn.
- [x] **6. Implement Streaming:** Connect the LLM provider's streaming output through the orchestrator to the UI for real-time text display.
- [x] **7. Prompt/Adventure Templates:** Add a simple mechanism to load initial system prompts from text files to start new adventures.