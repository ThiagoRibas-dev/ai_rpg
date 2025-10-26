# AI-RPG

AI-driven roleplay/text-adventure frontend with:
- Pluggable LLM providers (Gemini and OpenAI-compatible, including llama.cpp).
- Structured outputs and deterministic tools (dice, rules checks, patches).
- Validated, versioned state via JSON-like patches.
- Optional RAG for lore/continuity.
- customtkinter GUI with streaming and tool event log.

## Quick start
1) Install
- Python 3.11+
- pip install -r requirements.txt

2) Environment
- LLM_PROVIDER=GEMINI or OPENAI
- Gemini:
  - GEMINI_API_KEY=...
  - GEMINI_API_MODEL=gemini-1.5-pro (or similar)
- OpenAI-compatible:
  - OPENAI_API_BASE_URL=http://localhost:8080/v1
  - OPENAI_API_KEY=sk-local
  - OPENAI_API_MODEL=your-model

3) Run
python main.py

4) First steps
- Add a “Game Master” system prompt in Prompt Manager.
- Start a new game, type an action, watch tool events in the right panel.
