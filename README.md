# AI-RPG

An AI-driven, tool-using text RPG engine designed for performance, accuracy, and deep customization.

-   **Pluggable LLM Providers:** Supports Gemini and any OpenAI-compatible server (e.g., llama.cpp).
-   **AI-Powered Game System Creation (Session Zero):** Collaboratively design your game's mechanics with the AI. Paste in a rules document, and the AI will analyze it to generate a structured game template.
-   **Optimized for Performance & Cost:** The prompt system is engineered to leverage the context caching of LLM APIs, significantly reducing token usage and speeding up turns.
-   **Deterministic & Auditable Gameplay:** Turns are driven by strictly-defined tools with Pydantic-validated inputs (`rng.roll`, `state.apply_patch`, `character.update`), ensuring predictable outcomes from AI decisions.
-   **Rich State & Memory:** Features a versioned SQLite database for game state, a ChromaDB vector store for semantic memory retrieval, and per-prompt World Info for lore.
-   **Advanced GUI:** Built with CustomTkinter, the interface includes a live tool log, detailed state inspectors (character, inventory, quests), a powerful memory management panel, and world info editor.

## Table of Contents

-   [Features](#features)
-   [Architecture at a Glance](#architecture-at-a-glance)
-   [Requirements](#requirements)
-   [Install & Configure](#install--configure)
-   [Run](#run)
-   [How a Turn Works](#how-a-turn-works)
-   [Performance via Prompt Engineering](#performance-via-prompt-engineering)
-   [GUI Tour](#gui-tour)
-   [Data & Storage](#data--storage)

## Features

-   **Two LLM Backends:** Gemini and OpenAI-compatible.
-   **Session Zero Flow:** Define custom game mechanics via schema tools in `SETUP` mode before seamlessly transitioning to `GAMEPLAY` mode.
-   **AI-Powered Rules Extraction:** Automatically generate game mechanics (attributes, skills, resources) from pasted rules text.
-   **Deterministic Tools:** A suite of tools with Pydantic-validated inputs ensures reliable game state manipulation.
-   **Advanced Memory System:** Features semantic search, keyword/tag filtering, manual create/edit/delete, and JSON import/export capabilities.
-   **World Info:** Per-prompt lore snippets with vector search for contextual recall.
-   **Turn Metadata:** Each turn's summary, tags, and importance are stored and searchable.
-   **Advanced GUI:** Includes chat bubbles, a real-time tool call/result panel, live state inspectors, and management dialogs for World Info and Memories.

## Architecture at a Glance

-   **Orchestrator & TurnManager:** Coordinates a multi-step turn workflow (Plan → Iterative Tool Selection → Execute → Narrate → Choices).
-   **ContextBuilder:** Separates static (cacheable) from dynamic (per-turn) prompt content to optimize LLM calls.
-   **State Management:** SQLite for structured, versioned data (sessions, game state, memories) and ChromaDB for vector embeddings (memories, world info, turns).
-   **Tool System:** Tools are auto-discovered from the `app/tools/builtin` directory, with strict Pydantic schemas defining their inputs and purpose.
-   **GUI:** A clean separation of concerns with `builders` for UI construction and `managers` for handling application logic.

## Requirements

-   Python 3.11+
-   An LLM API Key (Gemini) or a running OpenAI-compatible server.
-   Internet access for first-time download of embedding models.

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
    # (Then edit .env with your credentials)
    ```

## Run

```shell
python main.py