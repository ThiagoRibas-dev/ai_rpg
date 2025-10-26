from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class MathEval(BaseModel):
    """Evaluates a math expression."""
    name: Literal["math.eval"] = "math.eval"
    expression: str = Field(..., description="Math expression, e.g., '2+3*4'")

class MemoryUpsert(BaseModel):
    """Upserts a memory into the database."""
    name: Literal["memory.upsert"] = "memory.upsert"
    kind: str = Field(..., description="The kind of memory to upsert. Allowed values: 'episodic', 'semantic', 'lore', 'user_pref'")
    content: str = Field(..., description="The content of the memory.")
    priority: int = Field(3, description="The priority of the memory.")
    tags: Optional[List[str]] = Field(None, description="A list of tags for the memory.")

class RagSearch(BaseModel):
    """Searches the RAG index for a query."""
    name: Literal["rag.search"] = "rag.search"
    query: str = Field(..., description="The query to search for.")
    k: int = Field(2, description="The number of chunks to return.")
    # TODO: Define a structured Filter model instead of a list of strings.
    filters: Optional[List[str]] = Field(None, description="A list of filters to apply, e.g., ['key:value'].")

class RngRoll(BaseModel):
    """Rolls a dice."""
    name: Literal["rng.roll"] = "rng.roll"
    dice: Optional[str] = Field(None, description="Dice spec, e.g., '1d20+3'.")
    dice_spec: Optional[str] = Field(None, description="Alias for dice.")

class Modifier(BaseModel):
    source: str = Field(..., description="The reason for the modifier (e.g., 'Player's Tech Skill', 'Magic Item Bonus').")
    value: int = Field(..., description="The value of the modifier.")

class ResolutionPolicy(BaseModel):
    type: str = Field(..., description="The type of resolution mechanic. Allowed value: 'skill_check'.")
    dc: int = Field(..., description="The final Difficulty Class for the check, as determined by the LLM.")
    base_formula: str = Field(..., description="The base dice roll formula (e.g., '1d20').")
    modifiers: Optional[List[Modifier]] = Field(None, description="A list of all modifiers the LLM has decided to apply.")

class RulesResolveAction(BaseModel):
    """Resolves an action using the rules engine."""
    name: Literal["rules.resolve_action"] = "rules.resolve_action"
    action_id: str = Field(..., description="A simple descriptive label for the action being resolved (e.g., 'Open Humming Lock').")
    actor_id: str = Field(..., description="The ID of the actor performing the action.")
    resolution_policy: ResolutionPolicy = Field(..., description="The complete policy for resolving the action, defined by the LLM.")
class Patch(BaseModel):
    op: str = Field(..., description="The operation to perform. Allowed values: 'add', 'replace', 'remove'")
    path: str = Field(..., description="The path to the value to modify.")
    value: Optional[str] = Field(None, description="The value to use, serialized as a string.")

class StateApplyPatch(BaseModel):
    """Applies a patch to the game state."""
    name: Literal["state.apply_patch"] = "state.apply_patch"
    entity_type: str = Field(..., description="The type of entity to patch.")
    key: str = Field(..., description="The key of the entity to patch.")
    patch: List[Patch] = Field(..., description="The patch to apply.")

class TimeNow(BaseModel):
    """Returns the current time."""
    name: Literal["time.now"] = "time.now"