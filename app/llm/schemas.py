from typing import List, Literal, Optional, Union, Any
from pydantic import BaseModel, Field

# A reusable JSON type to avoid recursion errors with Pydantic's schema generator.
JSONValue = Union[str, int, float, bool, dict, List]


class ToolCall(BaseModel):
    """Represents a single call to a tool from the LLM."""

    name: str = Field(
        ...,
        description="The name of the tool to call.",
        example="state_query",
    )
    arguments: Any = Field(
        default_factory=dict,
        description="The JSON-formatted string arguments for the tool.",
        example='{"entity_type": "character", "key": "player", "query": "gold"}',
    )


class PatchOp(BaseModel):
    """A single operation within a JSON Patch, as defined by RFC 6902."""

    op: Literal["add", "remove", "replace"] = Field(
        description="The operation to perform.",
        example="replace",
    )
    path: str = Field(
        description="A JSON Pointer path to the value to be operated on.",
        example="/stats/hp",
    )
    value: Optional[JSONValue] = Field(
        default=None,
        description="The value to be used for 'add' or 'replace' operations.",
        example=90,
    )


class Patch(BaseModel):
    """A collection of patch operations to be applied to a specific game entity."""

    entity_type: str = Field(
        description="The type of the entity to patch (e.g., 'character', 'location').",
        example="character",
    )
    key: str = Field(
        description="The unique key identifying the specific entity instance.",
        example="player",
    )
    ops: List[PatchOp] = Field(
        description="A list of patch operations to apply to the entity."
    )
class WorldTickOutcome(BaseModel):
    """The simulated outcome of an NPC's off-screen actions during a time skip."""

    outcome_summary: str = Field(
        ...,
        description="A brief, one-sentence summary of what happened as a result of the NPC's directive. This will become a memory if significant.",
        example="The town guard captain, while patrolling, discovered tracks leading to a hidden goblin den.",
    )
    is_significant: bool = Field(
        ...,
        description="Whether this outcome is significant enough to create a persistent memory for the player to potentially discover.",
        example=True,
    )
    proposed_patches: List[Patch] = Field(
        default_factory=list,
        description="A list of state changes to apply to the world as a result of this outcome. E.g., updating an NPC's inventory, location, or a relationship.",
    )


class ActionChoices(BaseModel):
    """A set of suggested actions for the player to choose from."""

    choices: List[str] = Field(
        description="A list of 3-5 concise action options for the user.",
        example=[
            "Go to the blacksmith.",
            "Enter the tavern.",
            "Check out the general store.",
            "Ask a passerby for directions.",
        ],
        min_length=3,
        max_length=5,
    )
