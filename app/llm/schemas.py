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


class TurnPlan(BaseModel):
    """The LLM's analysis of the player's intent and the strategic plan for the turn."""

    analysis: str = Field(
        description="A brief, one or two-sentence analysis of the player's last message, identifying their core intent.",
        example="The player wants to buy a sword from the blacksmith.",
    )
    plan_steps: List[str] = Field(
        description="A step-by-step logical plan of what the AI will do this turn before responding. This includes identifying necessary tool calls.",
        example=[
            "1. Check the player's current gold using state.query.",
            "2. See what swords the blacksmith has in stock using state.query.",
        ],
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


class MemoryIntent(BaseModel):
    """An instruction from the LLM to create or update a memory."""

    kind: Literal["episodic", "semantic", "lore", "user_pref"] = Field(
        description="The category of the memory.",
        example="episodic",
    )
    content: str = Field(
        description="The detailed content of the memory.",
        example="The player met a mysterious old man in the Whispering Woods who gave them a cryptic map.",
    )
    priority: Optional[int] = Field(
        default=None,
        ge=1,
        le=5,
        description="The importance of the memory (1=low, 5=high).",
        example=4,
    )
    tags: Optional[List[str]] = Field(
        default_factory=list,
        description="Keywords or tags to make the memory easily searchable.",
        example=["quest", "map", "npc_interaction"],
    )


class ResponseStep(BaseModel):
    """The LLM's main output for a turn, including the response text and any proposed changes."""

    response: str = Field(
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

    turn_summary: str = Field(
        description="A one-sentence summary of what happened this turn.",
        example="The player arrived in the city of Eldoria and decided to visit the blacksmith.",
    )
    turn_tags: List[str] = Field(
        description="3-5 tags categorizing this turn.",
        example=["exploration", "city", "decision"],
    )
    turn_importance: int = Field(
        ge=1,
        le=5,
        description="How important this turn is to the overall story (1=minor, 5=critical).",
        example=3,
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


class AuditResult(BaseModel):
    """The result of an audit on the game state or LLM's actions."""

    ok: bool = Field(
        description="Whether the audit passed without issues.",
        example=True,
    )
    notes: Optional[str] = Field(
        default=None,
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
