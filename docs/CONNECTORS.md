# Connectors

Connectors are responsible for communicating with the underlying LLM APIs.

## Interface (`app.llm.llm_connector.LLMConnector`)

- `get_streaming_response(prompt: str) -> generator[str]`:
  Streams a response from the LLM, yielding text chunks.

- `get_structured_response(prompt: str, tools: list[dict], output_schema: Type[BaseModel]) -> dict`:
  Requests a JSON object from the LLM that conforms to the `output_schema`.

## Gemini (`app.llm.gemini_connector.GeminiConnector`)

- **Strategy**: Uses Gemini's "Structured Output" feature.
- `get_structured_response` is implemented by passing the Pydantic `output_schema` directly to the `response_schema` parameter in the `generation_config`.
- The `tools` parameter is **ignored**. We do not use Gemini's function-calling feature for structured output to avoid schema compatibility issues (`$ref`, `anyOf`, etc.). Tool schemas are only passed in the text of the prompt for the model's reference.

## OpenAI-compatible (`app.llm.openai_connector.OpenAIConnector`)

- **Strategy**: Uses the `chat.completions` endpoint with `response_format={"type": "json_object"}`.
- To enforce the schema, the JSON schema of the Pydantic `output_schema` is included in the system prompt, instructing the model to return a matching JSON object.
- Streaming is handled by iterating over the server-sent events (SSE) delta chunks.