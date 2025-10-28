from typing import List, Optional, Literal, Any
from pydantic import BaseModel, Field

# A reusable JSON type to avoid recursion errors with Pydantic's schema generator.
JSONValue = Any

class ToolCall(BaseModel):
    name: str
    arguments: Optional[str] = None

class TurnPlan(BaseModel):
    thought: str
    tool_calls: List[ToolCall]

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
    narrative: str
    proposed_patches: List[Patch]
    memory_intents: List[MemoryIntent]
