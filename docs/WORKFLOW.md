# Turn workflow

## Phases
- Preprocess
  - Slash-commands (/roll 1d20), trivial state reads, context window trim.
- Plan (TurnPlan)
  - Model chooses tools and arguments (validated by schema).
- Tools
  - rules.skill_check, rng.roll, rag.search (timeboxed), time.now, etc.
  - Tool events stream to the UI.
- Narrative (NarrativeStep)
  - Conditioned on tool results; proposes patches and memories.
- Validate + Commit
  - Apply patches, upsert memory, persist events.
- Finish
  - Save assistant message, tool logs, latencies.

## Latency
- TTFB: 400–700 ms (remote), 200–400 ms (local).
- RAG timebox: ≤200 ms; don’t block narrative.