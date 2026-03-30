from typing import Any

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str = Field(
        ...,
        description="Message role: 'user', 'assistant', 'system', or 'tool'.",
    )
    content: str | None = Field(
        None,
        description="Text content of the message; may be None for pure tool calls.",
    )
    thought: str | None = Field(
        None,
        description="Thinking process or reasoning behind the response (e.g. for Gemini thinking models).",
    )
    thought_signature: str | None = Field(
        None,
        description="Internal signature for thinking parts required by some Gemini models.",
    )
    tool_calls: list[dict[str, Any]] | None = Field(
        None,
        description="List of tool calls produced by the assistant for this turn (normalized format).",
    )
    tool_call_id: str | None = Field(
        None,
        description="For tool messages: ID of the tool call this result relates to.",
    )
    name: str | None = Field(
        None,
        description="For tool messages: name of the tool that produced this result.",
    )
