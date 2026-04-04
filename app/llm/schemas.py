from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

# A reusable JSON type to avoid recursion errors with Pydantic's schema generator.
JSONValue = str | int | float | bool | dict | list


class ToolCall(BaseModel):
    """Represents a single call to a tool from the LLM."""

    name: Annotated[
        str,
        Field(
            description="The name of the tool to call.",
            examples=["state_query"],
        ),
    ]

    arguments: Annotated[
        dict[str, Any],
        Field(
            description="The JSON-formatted string arguments for the tool.",
            examples=[
                '{"entity_type": "character", "key": "player", "query": "gold"}'
            ],
        ),
    ] = {}


class PatchOp(BaseModel):
    """A single operation within a JSON Patch, as defined by RFC 6902."""

    op: Annotated[
        Literal["add", "remove", "replace"],
        Field(
            description="The operation to perform.",
            examples=["replace"],
        ),
    ]

    path: Annotated[
        str,
        Field(
            description="A JSON Pointer path to the value to be operated on.",
            examples=["/stats/hp"],
        ),
    ]

    value: Annotated[
        JSONValue | None,
        Field(
            description="The value to be used for 'add' or 'replace' operations.",
            examples=[90],
        ),
    ] = None


class Patch(BaseModel):
    """A collection of patch operations to be applied to a specific game entity."""

    entity_type: Annotated[
        str,
        Field(
            description="The type of the entity to patch (e.g., 'character', 'location').",
            examples=["character"],
        ),
    ]

    key: Annotated[
        str,
        Field(
            description="The unique key identifying the specific entity instance.",
            examples=["player"],
        ),
    ]

    ops: Annotated[
        list[PatchOp],
        Field(description="A list of patch operations to apply to the entity."),
    ]


class WorldTickOutcome(BaseModel):
    """The simulated outcome of an NPC's off-screen actions during a time skip."""

    outcome_summary: Annotated[
        str,
        Field(
            description="A brief, one-sentence summary of what happened as a result of the NPC's directive.",
            examples=[
                "The town guard captain discovered tracks leading to a hidden goblin den."
            ],
        ),
    ]

    is_significant: Annotated[
        bool,
        Field(
            description="Whether this outcome is significant enough to create a persistent memory.",
            examples=[True],
        ),
    ]

    proposed_patches: Annotated[
        list[Patch],
        Field(
            description="A list of state changes to apply to the world.",
        ),
    ] = []


class TurnFinalOutput(BaseModel):
    """Combined output for final turn processing (actions + metadata)."""

    choices: Annotated[
        list[str],
        Field(
            description="A list of 3-5 concise action options the player could take next.",
            examples=[
                [
                    "Go to the blacksmith.",
                    "Enter the tavern.",
                    "Roll a check to jump the chasm.",
                ]
            ],
            min_length=3,
            max_length=5,
        ),
    ]

    summary: Annotated[
        str,
        Field(
            description="Concise 1-3 sentence summary of what happened this scene.",
            max_length=512,
        ),
    ]

    tags: Annotated[
        list[str],
        Field(
            description="Tags in snake_case that describe the scene.",
            max_length=12,
        ),
    ] = []

    importance: Annotated[
        int,
        Field(
            description="1-5 importance rating for retrieval (1 = unimportant, 5 = major).",
            ge=1,
            le=5,
        ),
    ] = 3


class TurnSuggestions(BaseModel):
    """High-speed extraction for action choices."""

    choices: Annotated[
        list[str],
        Field(
            description="A list of 3-5 action options the player could take next.",
            min_length=3,
            max_length=5,
        ),
    ]


class TurnMetadata(BaseModel):
    """Background extraction for narration summary and indexing."""

    summary: Annotated[
        str,
        Field(
            description="Concise 1-3 sentence summary of what happened this scene.",
            max_length=512,
        ),
    ]

    tags: Annotated[
        list[str],
        Field(
            description="Tags in snake_case that describe the scene.",
            max_length=12,
        ),
    ] = []

    importance: Annotated[
        int,
        Field(
            description="1-5 importance rating for retrieval (1 = unimportant, 5 = major).",
            ge=1,
            le=5,
        ),
    ] = 3


class CharacterBasicInfo(BaseModel):
    """Basic identity info for a character."""

    name: Annotated[
        str,
        Field(
            description="The name of the character.",
            examples=["Elara the Brave"],
        ),
    ]

    concept: Annotated[
        str,
        Field(
            description="A high-level concept or elevator pitch for the character.",
            examples=["A stoic elven ranger seeking lost artifacts."],
        ),
    ]

    is_player: Annotated[
        bool,
        Field(
            description="Whether this character is a player character (True) or NPC (False).",
            examples=[True],
        ),
    ]


class CharacterBackground(BaseModel):
    """Narrative background for a character."""

    goals: Annotated[
        list[str],
        Field(
            description="A list of the character's primary goals.",
            examples=[["Find the lost city of Oakhaven", "Avenge my father"]],
        ),
    ]

    motivation: Annotated[
        str,
        Field(
            description="The character's primary motivation.",
            examples=["To bring honor to my family."],
        ),
    ]


class CharacterAppearance(BaseModel):
    """Visual descriptions for a character."""

    traits: Annotated[
        list[str],
        Field(
            description="Distinctive physical or personality traits.",
            examples=[["Stoic", "Scar across left eye"]],
        ),
    ]


class LocationBasicInfo(BaseModel):
    """Basic info for a location."""

    name: Annotated[
        str,
        Field(
            description="The name of the location.",
            examples=["The Rusty Dragon Inn"],
        ),
    ]
