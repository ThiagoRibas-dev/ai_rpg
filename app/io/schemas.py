from typing import List, Optional, Literal, Any
from pydantic import BaseModel, Field

# A reusable JSON type to avoid recursion errors with Pydantic's schema generator.
JSONValue = Any


class ToolCall(BaseModel):
    name: str = Field(..., description="The name of the tool to call.")
    arguments: str = Field(
        ..., description="The JSON-formatted string arguments for the tool."
    )


class TurnPlan(BaseModel):
    player_input_analysis: str = Field(
        ...,
        description="My analysis of player's intent, specially their latest message",
    )
    tool_calls: List[ToolCall] = Field(default_factory=list)
    plan: str = Field(
        ...,
        description="My plan for how I'll respond to the player, based on the history so far, my analysis of their input, the tools I called, etc.",
    )


class PatchOp(BaseModel):
    op: Literal["add", "remove", "replace"]
    path: str
    value: Optional[JSONValue] = None


class Patch(BaseModel):
    entity_type: str
    key: str
    ops: List[PatchOp]


class MemoryIntent(BaseModel):
    kind: Literal["episodic", "semantic", "lore", "user_pref"]
    content: str
    priority: Optional[int] = Field(None, ge=1, le=5)
    tags: Optional[List[str]] = None


class NarrativeStep(BaseModel):
    response: str
    proposed_patches: List[Patch] = Field(default_factory=list)
    memory_intents: List[MemoryIntent] = Field(default_factory=list)

    # 🆕 Turn metadata (no extra LLM call!)
    turn_summary: str = Field(
        ..., description="One-sentence summary of what happened this turn"
    )
    turn_tags: List[str] = Field(
        ...,
        description="3-5 tags categorizing this turn (e.g., 'combat', 'dialogue', 'discovery')",
    )
    turn_importance: int = Field(
        ...,
        description="How important is this turn? (1=minor detail, 3=normal, 5=critical plot point)",
    )


class ActionChoices(BaseModel):
    """
    A set of 3 concise action choices for the user to select from.
    Each choice should be a short, actionable statement that the player can say or do.
    """

    choices: List[str] = Field(
        ...,
        description="A list of concise action options for the user.",
        min_length=3,
        max_length=5,
    )


class AuditResult(BaseModel):
    ok: bool = True
    notes: Optional[str] = None
    proposed_patches: Optional[List[Patch]] = Field(default_factory=list)
    memory_updates: Optional[List[MemoryIntent]] = Field(default_factory=list)
