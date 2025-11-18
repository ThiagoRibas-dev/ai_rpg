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

## v6: Dynamic AI-Defined Game Mechanics

**Goal:** Evolve the AI-RPG engine from fixed rules to dynamic, AI-defined mechanics through collaborative "Session Zero" worldbuilding, combined with async UX improvements and robust schema validation.

**Key Phases:**
*   **Phase 1: Foundation** (Hybrid Schema + Session Zero)
*   **Phase 2: Async UX** (Responsive UI)
*   **Phase 3: High-Level Tools** (Schema-Aware Operations)
*   **Phase 4: Polish** (Export, Validation, UI)

## v7: Prompt Caching Optimization using Response Sufixes

*   **Separation of Static and Dynamic prompts using Response Prefix:** Implemente a complete prompt caching optimization system that separates static (cacheable) content from dynamic (per-turn) content, using response prefilling/suffixes to inject phase-specific instructions and context.
*   **Addition of Stage indicatior to the UI:** Add an indicator at the top of the Chat UI to display the current game stage (SETUP, GAMEPLAY).
*   **Tool Schema Refactor and Prompt Simplification:** Enrich tool schemas, remove redundant guidelines, and simplify prompt structures.

## v8: Game Prompt creation and SETUP game mode (Session Zero) refinements

*   **Database Schema Extension for Initial Messages:** Add `initial_message` column to the prompts table, update the Prompt model and all repository CRUD methods to support storing and retrieving a pre-written opening message that the Game Master will use when starting new sessions.

*   **Removal of Deprecated Memory Field from UI:** Remove the Memory textbox from the Advanced Context panel (a legacy field replaced by the dynamic memory retrieval system), update all related UI builders, managers, and session context methods to use only the Author's Note field.

*   **Three-Field Prompt Creation Dialog:** Replace simple input dialogs with a proper modal form (`PromptDialog`) containing Name, Content (system prompt), and Initial Message fields, providing better UX and validation for prompt creation and editing workflows.

*   **Initial Message Injection on Session Creation:** Automatically add the prompt's `initial_message` as the first assistant message when creating a new game session, ensuring players immediately see the Game Master's opening setup question in the chat history.

*   **SETUP Mode Scaffolding System:** Implement automatic injection of initial JSON structure (character/inventory/location templates) when a new game enters SETUP mode, providing the AI with a foundation to build upon rather than creating entities from scratch, with optional genre-specific suggestions (fantasy/sci-fi/horror/cyberpunk).

## V9: Rules Pre-processing and Template Management

*   **AI-Generated Game Templates:** Introduce a new feature that allows users to input raw rules documents (SRD, homebrew, etc.) from which the AI can automatically generate structured game templates. These templates capture core mechanics like attributes, resources, skills, and action economy.
*   **Rich Template Schema:** Implement a comprehensive Pydantic model (`GameTemplate`) to represent the structured game mechanics, ensuring semantic clarity and consistency for AI processing.
*   **Lean System Prompt Integration:** Utilize the generated game templates to create a highly compressed, "lean" schema reference that is injected into the AI's system prompt. This significantly reduces token usage while still providing the AI with essential game mechanic information.
*   **On-Demand Schema Query Tool:** Develop a `schema.query` tool that allows the AI to dynamically look up detailed information about game mechanics (attributes, skills, classes, etc.) from the active game template. This enables the AI to "ask" for rules details as needed, rather than memorizing the entire ruleset.
*   **Streamlined Session Setup:** New game sessions can now automatically inherit the AI-generated game template from the selected prompt, drastically reducing the manual setup time for new games.
*   **Enhanced Prompt Management UI:** Update the prompt creation/editing dialog to include fields for rules document input and a preview of the AI-generated template, providing a more intuitive user experience for defining game systems.

## V10: Sequential Game Template Generation
*   **Refactoring of single-shot Game Template Generation:** Refactor the single-shot `GameTemplate` generation into a more robust, multi-step pipeline. This approach improves reliability, quality, and enable context-passing between generation steps.

## V11 Prompt Template Refactoring for LLM Caching

**Goal:** Refactor `TemplateGenerationService` and its associated prompts to use a single, static system prompt for core instructions and rules, moving step-specific tasks into the user message. This optimizes for LLM providers utilizing prompt caching.

## v12: Enhancements to the state model

**Goal:** This version focuses on giving Non-Player Characters (NPCs) and the world itself a greater sense of agency, while making the AI's interaction with the state more intelligent, nuanced, and robust.

*   **World Persistence & Agency ("The World Tick"):**
    *   Implement an "off-screen" simulation system that processes NPC directives and world events during significant time skips.
    *   This allows the world to change and evolve independently of the player's direct actions, creating emergent story hooks and a sense of a living world.

*   **Deep NPC Modeling (`NpcProfile` & Relationships):**
    *   Introduce a dedicated `NpcProfile` entity to explicitly track an NPC's personality, motivations, and knowledge.
    *   Evolve the relationship model from simple strings to a structured object with quantifiable metrics (e.g., Trust, Attraction), giving the AI concrete data for nuanced roleplaying.

*   **Intelligent Scene & Party Management:**
    *   Implement a "Scene" entity to manage groups of characters as a single, atomic unit.
    *   Provide high-level tools for group actions (e.g., moving the entire party), preventing state inconsistencies and simplifying the AI's planning logic.

*   **Context-Aware Memory Retrieval:**
    *   Enhance the memory retrieval system to prioritize memories related to the characters and relationships currently active in the scene.
    *   This ensures the AI always has the most relevant interpersonal context, maintaining emotional continuity even in very long-running games.

## v13: Schema Generalization and AI-Assisted Rules Curation

**Goal:** Evolve the game template system from a rigid, pre-defined schema to a highly flexible, descriptive structure that can accurately model a wider variety of TTRPGs, including narrative-first and mechanically unique systems. This is paired with a new "human-in-the-loop" UI for rules processing that dramatically improves AI accuracy and user control.

*   **Generalized Data Models (`Mechanic`, `Trackable`):**
    *   Introduce a universal `Mechanic` block to replace separate definitions for rules, skills, and actions. This new model can describe any game procedure by its trigger, cost, resolution steps, and narrative outcomes, gracefully handling systems like *Blades in the Dark*'s "Position & Effect" or *Call of Cthulhu*'s "Pushing a Roll."
    *   Introduce a generalized `Trackable` model to replace the rigid `ResourceDefinition`. This can model anything from a simple HP pool to a segmented progress clock, a single reputation meter, or a list of status effects, using "thresholds" to define narrative consequences.
    *   Add a `GenerativeSystem` model to explicitly describe component-based systems (e.g., *Ars Magica*'s Verb+Noun magic), which were previously impossible to represent.

*   **Hybrid Character Schema (Core + Custom):**
    *   Refactor the character state model to include a small set of "canonical" fixed fields for ubiquitous concepts like Health (`hp`), Name, and Level.
    *   All other game-specific stats and resources will be modeled using the new flexible `Trackable` and `Mechanic` blocks. This provides UI consistency for common features while retaining maximum flexibility for unique game systems.

*   **AI-Powered Rules Organization with User Review:**
    *   Enhance the "New Prompt" dialog with an AI-powered pre-processing step. The user can paste an entire, unorganized rules document into a single text field.
    *   An "Analyze & Organize Rules" button will trigger an AI call that categorizes the text into logical chunks (e.g., Core Rules, Character Creation, Special Systems).
    *   These AI-generated chunks will then populate a series of dedicated text fields in the UI, allowing the user to **review, edit, and correct** the AI's categorization.
    *   This "human-in-the-loop" workflow combines the ease of automation with the accuracy of human oversight, ensuring the final template generation pipeline receives perfectly organized and contextually rich data.