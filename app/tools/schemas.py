from typing import Literal

from pydantic import BaseModel, Field

from app.models.vocabulary import MemoryKind

# --- ATOMIC GAMEPLAY TOOLS ---


class Adjust(BaseModel):
    """
    Add or subtract from a numeric value (Resource or Attribute).
    Use this for damage, healing, spending resources, or modifying stats.
    """

    name: Literal["adjust"] = "adjust"
    target: str = Field(
        "player", description="Entity key (e.g. 'player', 'goblin_1', 'npc_bartender')."
    )
    path: str = Field(
        ...,
        description="Full path to the field (e.g. 'resources.hp.current', 'attributes.str').",
    )
    delta: int | float = Field(
        ..., description="Amount to add (positive) or subtract (negative)."
    )
    reason: str = Field(
        "Action",
        description="Brief reason for the change (e.g. 'Goblin damage', 'Potion').",
    )


class Set(BaseModel):
    """
    Set a field to a specific absolute value.
    Use this for changing modes, toggles, equipping items, or overriding values.
    """

    name: Literal["set"] = "set"
    target: str = Field(
        "player", description="Entity key (e.g. 'player', 'goblin_1', 'npc_bartender')."
    )
    path: str = Field(
        ...,
        description="Full path to the field (e.g. 'status.is_hiding', 'inventory.weapon').",
    )
    value: int | float | bool | str | dict | list = Field(
        ..., description="The new value to set."
    )
    reason: str = Field("Update", description="Brief reason for the change.")


class Mark(BaseModel):
    """
    Mark or clear boxes on a Track (e.g. Stress, Wounds, Clocks).
    """

    name: Literal["mark"] = "mark"
    target: str = Field(
        "player", description="Entity key (e.g. 'player', 'goblin_1', 'npc_bartender')."
    )
    path: str = Field(
        ...,
        description="Path to the track field (e.g. 'resources.stress', 'status.harm').",
    )
    count: int = Field(
        1, description="Number of boxes to mark (positive) or clear (negative)."
    )


class Roll(BaseModel):
    """
    Roll dice to resolve an action or check.
    """

    name: Literal["roll"] = "roll"
    formula: str = Field(
        ..., description="Dice notation (e.g. '1d20+5', '2d6', '1d100')."
    )
    reason: str = Field(
        ...,
        description="Context for the roll (e.g. 'Attack vs AC 15', 'Sanity Check').",
    )


class Move(BaseModel):
    """
    Move the party to a different location.
    """

    name: Literal["move"] = "move"
    destination: str = Field(
        ..., description="The ID/Key of the target location (e.g. 'loc_tavern')."
    )


class Note(BaseModel):
    """
    Save a note (a memory, fact, event, game rule, or preference) in the game history log for future reference.
    """

    name: Literal["note"] = "note"
    content: str = Field(..., description="The text to remember.")
    kind: MemoryKind = Field(
        MemoryKind.EPISODIC, description="Type of memory. Use 'episodic' for events, 'semantic' for general facts."
    )
    tags: list[str] = Field(
        ..., description="Names, tags, keywords, or categories to help retrieve this memory later."
    )


# --- UTILITY / SETUP TOOLS

class StateQuery(BaseModel):
    """
    Look up details about a known entity (NPC, location, quest, etc.) by key.
    Use the World Index to find valid keys. Use json_path="." for full data.
    """
    name: Literal["state.query"] = "state.query"
    entity_type: str = Field(..., description="Entity type: 'character', 'location', 'quest', etc.")
    key: str = Field(..., description="Entity key from the World Index (e.g. 'npc_captain_voss', 'tavern_rusty_nail'). Use '*' for all of a type.")
    json_path: str = Field(".", description="JSON path to drill into (use '.' for full entity data).")


class NpcSpawn(BaseModel):
    """
    Spawn a new NPC into the game world at a specific location.
    """
    name: Literal["npc.spawn"] = "npc.spawn"
    key: str = Field(...)
    name_display: str = Field(...)
    visual_description: str = Field(...)
    stat_template: str = Field(...)
    initial_disposition: Literal["hostile", "neutral", "friendly"] = "neutral"
    location_key: str | None = None


class LocationCreate(BaseModel):
    """
    Create a new location and define its visual/sensory details and neighbors (connection to other locations).
    """
    name: Literal["location.create"] = "location.create"
    key: str = Field(...)
    name_display: str = Field(...)
    description_visual: str = Field(...)
    description_sensory: str = Field(...)
    type: str = Field(...)
    neighbors: dict[str, str] = Field(default_factory=dict)


class ContextRetrieve(BaseModel):
    """
    Retrieve relevant piece of information (lore, rules, events, etc) based on the query text.
    """

    name: Literal["context.retrieve"] = "context.retrieve"
    query: str = Field(
        ..., description="Query text (usually derived from last user action)."
    )
    kinds: list[MemoryKind] = Field(
        default_factory=lambda: [MemoryKind.EPISODIC, MemoryKind.SEMANTIC, MemoryKind.LORE, MemoryKind.RULE]
    )
    limit: int = Field(8, ge=1, le=20)
