# Turn Workflow

Fast path vs full pipeline to minimize latency.

**1) Preprocess**
- Detect slash-commands or equivalent input via a menu (/roll 1d20, /inventory) handled locally.
- Language detect, short-circuit trivial echo/state reads.

**2) Retrieve context**
- Short-term transcript window (N recent turns)
- RAG prefetch: last user input → embeddings search (non-blocking, with timeout ~150–300 ms)
- State snapshot: only relevant entities requested via selectors (scene, party, location)

**3) Planning (schema `TurnPlan`)**
- Small prompt to model: “Do we need rag/tools? Which ones?” Response validated.

**4) Tool execution**
- Run in parallel where safe: rag.search, time.now, math.eval, asset.resolve
- RNG/tool results streamed to UI as they complete

**5) Narrative + Proposals (schema `NarrativeStep`)**
- Model streams narrative
- Proposes `StatePatch` and `MemoryIntent` arrays

**6) Validation and commit**
- Engine validates ops; if safe, commit and display “State updated”
- Memory dedupe/scoring; low-priority memories can be queued for batch

**7) Finalization**
- Save messages, tool events, patches; compute token/latency; emit telemetry