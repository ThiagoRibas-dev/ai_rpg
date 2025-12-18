# AI-RPG

An AI-driven, tool-using text RPG engine designed for performance, accuracy, and deep customization.

-   **Architecture:** "Lego Protocol" – Uses strict System Manifests and Prefabs to ensure the AI follows game rules deterministically.
-   **Pluggable LLM Providers:** Supports Gemini and OpenAI-compatible servers.
-   **Context Caching:** Optimized prompt engineering to leverage API-side caching for massive context windows at low cost.
-   **NiceGUI Interface:** A modern, reactive web-based UI with real-time state inspectors.

## Features

-   **Manifest-Driven Gameplay:** The engine doesn't just "guess" rules. It loads a JSON Manifest (e.g., D&D 5e, Call of Cthulhu) and enforces stats, dice mechanics, and resource pools via code.
-   **Session Zero Wizard:** Create a new campaign by loading a preset system OR pasting raw rules text. The AI extracts a new System Manifest from your text automatically.
-   **Atomic Toolset:** The AI interacts with the world using 6 precise tools: `Adjust`, `Set`, `Roll`, `Mark`, `Move`, `Note`.
-   **ReAct Logic:** Uses a "Reason + Act" loop to handle complex turns (e.g., "Roll to hit" -> "See result" -> "Apply Damage" -> "Narrate" in one turn).
-   **Visual State Inspectors:** Live character sheets, inventory lists, and quest logs that render differently based on the active game system (e.g., plotting Stress Tracks vs. HP Pools).
-   **Rich Memory:** Semantic search (RAG) for Lore and past Events.

## Architecture at a Glance

-   **Orchestrator:** Manages the application lifecycle and UI bridge.
-   **ReActTurnManager:** The game loop. It injects the `SystemManifest` into the context, allowing the LLM to understand valid moves.
-   **Validation Pipeline:** A middleware layer that runs after every AI action to enforce rules (e.g., calculating AC from Dex, clamping HP).
-   **State Management:** SQLite for structured data (versioned Entity-Component system) and ChromaDB for vector embeddings.
-   **GUI:** Built with **NiceGUI**. Includes chat, tactical maps, and dynamic attribute inspectors.

## Requirements

-   Python 3.11+
-   An LLM API Key (Gemini, OpenAi, OpenRouter) or a local OpenAI-compatible endpoint (llama.cpp, vLLM).

## Install & Configure

1.  **Create and activate a virtual environment:**
    ```shell
    python -m venv .venv
    source .venv/bin/activate  # Linux/macOS
    .\.venv\Scripts\Activate.ps1 # Windows PowerShell
    ```

2.  **Install dependencies:**
    ```shell
    pip install -r requirements.txt
    ```

3.  **Configure your environment:** Copy `.exampleenv` to `.env` and fill in your LLM provider details.
    ```shell
    cp .exampleenv .env
    ```

## Run

```shell
python main.py