from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str = Field(
        ...,
        description="Message role: 'user', 'assistant', 'system', or 'tool'.",
    )
    content: Optional[str] = Field(
        None,
        description="Text content of the message; may be None for pure tool calls.",
    )
    tool_calls: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="List of tool calls produced by the assistant for this turn (normalized format).",
    )
    tool_call_id: Optional[str] = Field(
        None,
        description="For tool messages: ID of the tool call this result relates to.",
    )
    name: Optional[str] = Field(
        None,
        description="For tool messages: name of the tool that produced this result.",
    )
