from pydantic import BaseModel, Field
from typing import List, Dict, Any

class ToolCall(BaseModel):
    """Represents a single tool call requested by the LLM."""
    name: str = Field(..., description="The name of the tool to call.")
    arguments: Dict[str, Any] = Field(..., description="The arguments to pass to the tool.")

class TurnPlan(BaseModel):
    """
    Represents the LLM's plan for the turn, including its thought process
    and any tool calls it intends to make.
    """
    thought: str = Field(..., description="The model's reasoning for its chosen actions.")
    tool_calls: List[ToolCall] = Field(default_factory=list, description="A list of tool calls to be executed.")

class StatePatch(BaseModel):
    """
    Represents a JSON Patch operation to be applied to the game state.
    Follows RFC 6902.
    """
    op: str = Field(..., description="The operation to perform (e.g., 'add', 'replace', 'remove').")
    path: str = Field(..., description="The JSON Pointer path to the target location.")
    value: Any = Field(None, description="The value to be used for the operation.")


class NarrativeStep(BaseModel):
    """
    Represents the final output of the turn, including the narrative text
    and any proposed changes to the game state or memory.
    """
    narrative: str = Field(..., description="The narrative text to be displayed to the user.")
    state_patch: List[StatePatch] = Field(default_factory=list, description="A list of JSON Patch operations to apply to the game state.")
    memory_intent: List[str] = Field(default_factory=list, description="A list of memories or observations to be stored.")