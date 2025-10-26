# Architecture

- GUI renders streamed tokens and inline tool events.
- Orchestrator executes a per-turn pipeline: Plan → Tools → Narrative → Patches/Memories.
- Provider adapters normalize Gemini and OpenAI-compatible APIs.
- Tools are deterministic functions with JSON schemas + Python handlers.
- Optional RAG for flavor and continuity.

## Data flow (one turn)
1) Build a planning prompt from recent history and state selectors.
2) LLM returns TurnPlan.tool_calls (structured).
3) Execute tools (parallel where safe).
4) LLM returns NarrativeStep with narrative + proposed_patches + memory_intents.
5) Engine validates/applies patches and stores memory.
6) Persist everything and render streaming output.