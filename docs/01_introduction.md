# Introduction

This document outlines the high-level goals and core user stories for the AI-RPG project.

## High-level goals
- Generic Text-adventure and roleplay frontend where the LLM is an orchestrator, not just a chat bot.
- Pluggable LLM backends: Google Gemini and any OpenAI-compatible API (including llama.cpp server).
- State-first: the model proposes what to persist; deterministic systems validate/apply patches.
- Schema-first orchestration: all model I/O uses structured outputs (JSON Schema) with strict validation.
- RAG for lore/world memory and long-term continuity.

## Core user stories
- Start a new adventure by creating a prompt.
- Type commands or roleplay; watch the scene evolve with streamed narrative.
- Inspect and edit world state (inventory, locations, NPCs, quest flags).
- See dice rolls and actions outcomes (deterministic tools).
- Switch model providers on the fly; resume the same session and state.
- Undo/redo last turn; view the action log of tool calls and patches.
