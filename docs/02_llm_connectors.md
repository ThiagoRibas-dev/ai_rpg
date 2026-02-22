# Connectors

Connectors are responsible for communicating with the underlying LLM APIs.
A couple of general rules when crafting response schemas that need to be followed are : Not using Dict or dict; Using clear, strict, scperific pydantic classes; Making sure that the LLM can only generate the desired results; 

## Interface (`app.llm.llm_connector.LLMConnector`)

- `get_streaming_response(system_prompt: str, chat_history: list[Message]) -> generator[str]`:
  Streams a response from the LLM, yielding text chunks. The `system_prompt` sets the initial context, and `chat_history` provides the conversational turn history.

- `get_structured_response(system_prompt: str, chat_history: list[Message], output_schema: Type[BaseModel]) -> dict`:
  Requests a JSON object from the LLM that conforms to the `output_schema`. The `system_prompt` sets the initial context, and `chat_history` provides the conversational turn history.

## Gemini (`app.llm.gemini_connector.GeminiConnector`)

- **Strategy**: Uses Gemini's "Structured Output" feature.
- `get_structured_response` is implemented by passing the Pydantic `output_schema` directly to the `response_schema` parameter in the `generation_config`.
- The `tools` parameter is **ignored**. We do not use Gemini's function-calling feature for structured output to avoid schema compatibility issues (`$ref`, `anyOf`, etc.). Tool schemas are only passed in the text of the prompt for the model's reference.

## OpenAI-compatible (`app.llm.openai_connector.OpenAIConnector`)

- **Strategy**: Uses the `chat.completions` endpoint with `response_format={"type": "json_object"}`.
- To enforce the schema, the JSON schema of the Pydantic `output_schema` is included in the system prompt, instructing the model to return a matching JSON object.
- Streaming is handled by iterating over the server-sent events (SSE) delta chunks.

## Notes

**Gemini API Schema Limitations:** A key architectural constraint is that the Google Gemini API's schema validation for structured JSON output is very strict. It does not support free-form dictionaries (e.g., `Dict[str, int]`) because they translate to a JSON schema with `"type": "object"` but no defined `"properties"`, which the API rejects. Furthermore, the `additionalProperties` field, a common way to define dictionaries in JSON Schema, is also not supported.
Some notes from the `types.py` file from google's genai library:
```
    response_schema: Optional[SchemaUnion] = Field(
        default=None,
        description="""The `Schema` object allows the definition of input and output data types.
        These types can be objects, but also primitives and arrays.
        Represents a select subset of an [OpenAPI 3.0 schema
        object](https://spec.openapis.org/oas/v3.0.3#schema).
        If set, a compatible response_mime_type must also be set.
        Compatible mimetypes: `application/json`: Schema for JSON response.
        """,
    )
    response_json_schema: Optional[Any] = Field(
        default=None,
        description="""Optional. Output schema of the generated response.
        This is an alternative to `response_schema` that accepts [JSON
        Schema](https://json-schema.org/). If set, `response_schema` must be
        omitted, but `response_mime_type` is required. While the full JSON Schema
        may be sent, not all features are supported. Specifically, only the
        following properties are supported: - `$id` - `$defs` - `$ref` - `$anchor`
        - `type` - `format` - `title` - `description` - `enum` (for strings and
        numbers) - `items` - `prefixItems` - `minItems` - `maxItems` - `minimum` -
        `maximum` - `anyOf` - `oneOf` (interpreted the same as `anyOf`) -
        `properties` - `additionalProperties` - `required` The non-standard
        `propertyOrdering` property may also be set. Cyclic references are
        unrolled to a limited degree and, as such, may only be used within
        non-required properties. (Nullable properties are not sufficient.) If
        `$ref` is set on a sub-schema, no other properties, except for than those
        starting as a `$`, may be set.""",
    )
  ```

**Gemini API Reference Code**

The following Python code snippet provides a reference for interacting directly with the Gemini API using the `google-genai` library. It demonstrates how to construct a schema manually, configure safety settings to block no content, and stream the response. This is an alternative to the Pydantic-based schema generation used in the `LLMConnector`.

```python
import base64
import os
from google import genai
from google.genai import types


def generate():
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    model = "gemini-2.5-flash"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text="""INSERT_INPUT_HERE"""),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        thinking_config = types.ThinkingConfig(
            thinking_budget=12875,
        ),
        safety_settings=[
            types.SafetySetting(
                category="HARM_CATEGORY_HARASSMENT",
                threshold="BLOCK_NONE",  # Block none
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_HATE_SPEECH",
                threshold="BLOCK_NONE",  # Block none
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                threshold="BLOCK_NONE",  # Block none
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT",
                threshold="BLOCK_NONE",  # Block none
            ),
        ],
        response_mime_type="application/json",
        response_schema=genai.types.Schema(
            type = genai.types.Type.OBJECT,
            required = ["example_arr", "reply"],
            properties = {
                "example_arr": genai.types.Schema(
                    type = genai.types.Type.ARRAY,
                    items = genai.types.Schema(
                        type = genai.types.Type.OBJECT,
                        required = ["example_str", "example_int", "example_num", "example_bool", "example_enum"],
                        properties = {
                            "example_str": genai.types.Schema(
                                type = genai.types.Type.STRING,
                            ),
                            "example_int": genai.types.Schema(
                                type = genai.types.Type.INTEGER,
                            ),
                            "example_num": genai.types.Schema(
                                type = genai.types.Type.NUMBER,
                            ),
                            "example_bool": genai.types.Schema(
                                type = genai.types.Type.BOOLEAN,
                            ),
                            "example_enum": genai.types.Schema(
                                type = genai.types.Type.STRING,
                                enum = ["enum_val1", "enum_val2"],
                            ),
                        },
                    ),
                ),
                "reply": genai.types.Schema(
                    type = genai.types.Type.STRING,
                ),
            },
        ),
    )

    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        print(chunk.text, end="")
