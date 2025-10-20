# LLM Provider Abstraction

Define one internal interface; adapters translate to provider specifics.

`ModelEvent` can be:
- `TokenDelta(text)`
- `ToolCallStart(name, arguments)`
- `ToolCallResult(name, result)`
- `StructuredOutput(obj)`
- `Error(e)`

Adapters:
- **GeminiAdapter**: maps `response_schema` to Gemini’s Structured Output; maps tools to Gemini’s tool calling.
- **OpenAICompatAdapter**: uses function calling + JSON Schema; llama.cpp server works here.

## Provider Specifics

### Gemini
- Use Structured Output for `TurnPlan`/`NarrativeStep` to avoid JSON parsing hacks
- Tools: map `ToolSpec` to Gemini Functions
- Supports parallel function calls; handle partial tool results streaming

### OpenAI-compatible (including llama.cpp server)
- Use function calling + JSON Schema; if schema rejection, switch to “json-only” assistant message
- SSE streaming: aggregate `delta.choices[0].delta`
- Handle server quirks (e.g., llama.cpp limits on tool definitions)