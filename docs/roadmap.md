# Roadmap

This document outlines the planned features and development milestones for the AI-RPG project.

## v1: Core Engine

*   **Narrative Engine:** A robust core engine for managing the game's narrative, including a flexible LLM connector system to support various models.
*   **Session Management:** The ability to save, load, and manage game sessions.
*   **GUI:** A functional user interface for interacting with the game, including a chat-style interface for the narrative.

## v2: Tool Infrastructure

*   **Tool System:** A system that allows the LLM to use tools to perform deterministic actions, such as rolling dice, checking rules, or managing inventory.
*   **GUI refactor:**  UI changes for easier prompt and session management. Tool calls as part of visible chat history.

## V3: Advanced Interaction and Context Control

*   **UI Refactoring with Collapsible Layout:** 
    *   The main control panel will be reorganized into collapsible sections (Sessions, Parameters, Context, etc.) to create a cleaner and more scalable user interface.
    *   The prompt management view, currently in a separate popup, will be integrated into the main UI.
*   **Advanced Context Management:**
    *   **Memory & Author's Note:** Users will have dedicated text areas to provide persistent, high-level instructions (Memory) and turn-specific guidance (Author's Note) to the LLM.
    *   **World Info System:** A keyword-based knowledge base will be implemented. Users can define entries that are dynamically injected into the prompt when their associated keywords appear in the recent conversation, providing a simple yet powerful RAG-like capability.
*   **Interactive User Choices:**
    *   At the end of each narrative turn, the AI will generate a set of 3 suggested actions or dialogue options.
    *   These options will be displayed as clickable buttons, allowing the user to guide the story with a single click instead of typing a response.

## v4: Simple Agentic Memory

*   **Core Functionality:** Fully integrate the existing `memory.upsert` tool into the orchestrator, allowing the LLM to autonomously extract key information from the conversation and store it as memories.
*   **Persistent Storage:** Upgrade the memory store from a temporary in-memory dictionary to a simple persistent solution (e.g., a JSON file or a lightweight database) so that memories are saved between game sessions.
*   **Memory Retrieval:** Implement a corresponding tool (e.g., `memory.query`) that allows the LLM to search and retrieve relevant memories based on kinds or tags to inform its responses.
*   **GUI Integration:** Add a new panel to the GUI that displays the list of created memories, allowing the user to see what the AI is remembering. This would provide the transparency you mentioned.

## v5: Advanced State Management and RAG

*   **State Management:** A structured system for managing the game state, including character sheets, inventory, and world state.
*   **RAG (Retrieval-Augmented Generation):** A system for retrieving information from a knowledge base, such as a rulebook or lore document, to provide more contextually relevant responses.

## v6: Extensibility and Intelligence

*   **Plugin Architecture:** A system that allows for the creation of third-party plugins to extend the game's functionality, such as new tools, content, or even core systems.
*   **Advanced Agency:** Exploration of more advanced AI techniques, such as multi-agent systems (e.g., a separate "Game Master" agent) and more sophisticated planning capabilities.
*   **Dynamic World:** Features that allow the game world to evolve and change in response to player actions, creating a more dynamic and immersive experience.sh
