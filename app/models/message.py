from typing import Annotated, Any

from pydantic import BaseModel, Field

from app.models.vocabulary import MessageRole


class Message(BaseModel):
    role: Annotated[
        MessageRole,
        Field(description="Message role: 'user', 'assistant', 'system', or 'tool'."),
    ]
    content: Annotated[
        str | None,
        Field(description="Text content of the message; may be None for pure tool calls."),
    ] = None
    thought: Annotated[
        str | None,
        Field(
            description="Thinking process or reasoning behind the response (e.g. for Gemini thinking models)."
        ),
    ] = None
    thought_signature: Annotated[
        str | None,
        Field(
            description="Internal signature for thinking parts required by some Gemini models."
        ),
    ] = None
    tool_calls: Annotated[
        list[dict[str, Any]] | None,
        Field(
            description="List of tool calls produced by the assistant for this turn (normalized format)."
        ),
    ] = None
    tool_call_id: Annotated[
        str | None,
        Field(
            description="For tool messages: ID of the tool call this result relates to."
        ),
    ] = None
    name: Annotated[
        str | None,
        Field(
            description="For tool messages: name of the tool that produced this result."
        ),
    ] = None
    turn_id: Annotated[
        str | None,
        Field(description="The unique ID of the turn this message belongs to."),
    ] = None
