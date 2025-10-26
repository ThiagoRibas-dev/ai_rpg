from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class ToolCall(BaseModel):
    name: str
    arguments: Optional[str] = None

class TurnPlan(BaseModel):
    thought: str
    tool_calls: List[ToolCall]

class PatchOp(BaseModel):
    op: Literal["add", "remove", "replace"]
    path: str
    value: Optional[str] = None

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
