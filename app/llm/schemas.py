from typing import List, Optional, Literal, Any
from pydantic import BaseModel, Field

# A reusable JSON type to avoid recursion errors with Pydantic's schema generator.
JSONValue = Any


class ToolCall(BaseModel):
    """Represents a single call to a tool from the LLM."""

    name: str = Field(
        ...,
        description="The name of the tool to call.",
        example="state_query",
    )
    arguments: str = Field(
        ...,
        description="The JSON-formatted string arguments for the tool.",
        example='{"entity_type": "character", "key": "player", "query": "gold"}',
    )


class TurnPlan(BaseModel):
    """The LLM's internal plan for its turn, including tool calls and response strategy."""

    player_input_analysis: str = Field(
        ...,
        description="The LLM's analysis of the player's intent and latest message.",
        example="The player wants to buy a sword. I need to check if they have enough gold and if there's a blacksmith in town.",
    )
    response_plan: str = Field(
        ...,
        description="The LLM's for the turn's response, after analyzing input and executing tools.",
        example="First, I'll describe the bustling market. Then, I'll have the blacksmith greet the player and show them the available swords. I'll mention the price and wait for the player's response.",
    )
    tool_calls: List[ToolCall] = Field(
        default_factory=list,
        description="The tools that will be executed based on the input analysis and the response plan.",
    )


class PatchOp(BaseModel):
    """A single operation within a JSON Patch, as defined by RFC 6902."""

    op: Literal["add", "remove", "replace"] = Field(
        ...,
        description="The operation to perform.",
        example="replace",
    )
    path: str = Field(
        ...,
        description="A JSON Pointer path to the value to be operated on.",
        example="/stats/hp",
    )
    value: Optional[JSONValue] = Field(
        None,
        description="The value to be used for 'add' or 'replace' operations.",
        example=90,
    )


class Patch(BaseModel):
    """A collection of patch operations to be applied to a specific game entity."""

    entity_type: str = Field(
        ...,
        description="The type of the entity to patch (e.g., 'character', 'location').",
        example="character",
    )
    key: str = Field(
        ...,
        description="The unique key identifying the specific entity instance.",
        example="player",
    )
    ops: List[PatchOp] = Field(
        ..., description="A list of patch operations to apply to the entity."
    )


class MemoryIntent(BaseModel):
    """An instruction from the LLM to create or update a memory."""

    kind: Literal["episodic", "semantic", "lore", "user_pref"] = Field(
        ...,
        description="The category of the memory.",
        example="episodic",
    )
    content: str = Field(
        ...,
        description="The detailed content of the memory.",
        example="The player met a mysterious old man in the Whispering Woods who gave them a cryptic map.",
    )
    priority: Optional[int] = Field(
        None,
        ge=1,
        le=5,
        description="The importance of the memory (1=low, 5=high).",
        example=4,
    )
    tags: Optional[List[str]] = Field(
        None,
        description="Keywords or tags to make the memory easily searchable.",
        example=["quest", "map", "npc_interaction"],
    )


class ResponseStep(BaseModel):
    """The LLM's main output for a turn, including the response text and any proposed changes."""

    response: str = Field(
        ...,
        description="The response text to be shown to the player.",
        example="The city of Eldoria bustles with life. You see a blacksmith's shop, a tavern, and a general store. What do you do?",
    )
    proposed_patches: List[Patch] = Field(
        default_factory=list,
        description="A list of state changes the LLM proposes based on the turn's events.",
    )
    memory_intents: List[MemoryIntent] = Field(
        default_factory=list,
        description="A list of memories the LLM wants to record from this turn.",
    )
    turn_summary: str = Field(
        ...,
        description="A one-sentence summary of what happened this turn.",
        example="The player arrived in the city of Eldoria and decided to visit the blacksmith.",
    )
    turn_tags: List[str] = Field(
        ...,
        description="3-5 tags categorizing this turn.",
        example=["exploration", "city", "decision"],
    )
    turn_importance: int = Field(
        ...,
        ge=1,
        le=5,
        description="How important this turn is to the overall story (1=minor, 5=critical).",
        example=3,
    )


class ActionChoices(BaseModel):
    """A set of suggested actions for the player to choose from."""

    choices: List[str] = Field(
        ...,
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


class AuditResult(BaseModel):
    """The result of an audit on the game state or LLM's actions."""

    ok: bool = Field(
        True,
        description="Whether the audit passed without issues.",
        example=True,
    )
    notes: Optional[str] = Field(
        None,
        description="Auditor's notes, explaining any issues found or suggestions for improvement.",
        example="The player's health should not be above the maximum health defined in the character sheet.",
    )
    proposed_patches: Optional[List[Patch]] = Field(
        default_factory=list,
        description="Corrective patches to fix any inconsistencies found during the audit.",
    )
    memory_updates: Optional[List[MemoryIntent]] = Field(
        default_factory=list,
        description="Memory updates to correct or add information based on the audit.",
    )
