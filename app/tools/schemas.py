from typing import Literal, Optional, Union

from pydantic import BaseModel, Field

# --- ATOMIC GAMEPLAY TOOLS ---

class Adjust(BaseModel):
    """
    Add or subtract from a numeric value (Resource or Attribute).
    Use this for damage, healing, spending resources, or modifying stats.
    """
    name: Literal["adjust"] = "adjust"
    path: str = Field(..., description="Full path to the field (e.g. 'resources.hp.current', 'attributes.str').")
    delta: Union[int, float] = Field(..., description="Amount to add (positive) or subtract (negative).")
    reason: str = Field("Action", description="Brief reason for the change (e.g. 'Goblin damage', 'Potion').")

class Set(BaseModel):
    """
    Set a field to a specific absolute value.
    Use this for changing modes, toggles, equipping items, or overriding values.
    """
    name: Literal["set"] = "set"
    path: str = Field(..., description="Full path to the field (e.g. 'status.is_hiding', 'inventory.weapon').")
    value: Union[int, float, bool, str, dict, list] = Field(..., description="The new value to set.")
    reason: str = Field("Update", description="Brief reason for the change.")

class Mark(BaseModel):
    """
    Mark or clear boxes on a Track (e.g. Stress, Wounds, Clocks).
    """
    name: Literal["mark"] = "mark"
    path: str = Field(..., description="Path to the track field (e.g. 'resources.stress', 'status.harm').")
    count: int = Field(1, description="Number of boxes to mark (positive) or clear (negative).")

class Roll(BaseModel):
    """
    Roll dice to resolve an action or check.
    """
    name: Literal["roll"] = "roll"
    formula: str = Field(..., description="Dice notation (e.g. '1d20+5', '2d6', '1d100').")
    reason: str = Field(..., description="Context for the roll (e.g. 'Attack vs AC 15', 'Sanity Check').")

class Move(BaseModel):
    """
    Move the party to a different location.
    """
    name: Literal["move"] = "move"
    destination: str = Field(..., description="The ID/Key of the target location (e.g. 'loc_tavern').")

class Note(BaseModel):
    """
    Record a memory, fact, or event in the game log.
    """
    name: Literal["note"] = "note"
    content: str = Field(..., description="The text to remember.")
    kind: Literal["event", "fact", "lore"] = Field("event", description="Type of memory.")

# --- UTILITY / SETUP TOOLS (Kept for compatibility/setup) ---

class StateQuery(BaseModel):
    name: Literal["state.query"] = "state.query"
    entity_type: str = Field(...)
    key: str = Field(...)
    json_path: str = Field(...)

class NpcSpawn(BaseModel):
    name: Literal["npc.spawn"] = "npc.spawn"
    key: str = Field(...)
    name_display: str = Field(...)
    visual_description: str = Field(...)
    stat_template: str = Field(...)
    initial_disposition: Literal["hostile", "neutral", "friendly"] = "neutral"
    location_key: Optional[str] = None

class LocationCreate(BaseModel):
    name: Literal["location.create"] = "location.create"
    key: str = Field(...)
    name_display: str = Field(...)
    description_visual: str = Field(...)
    description_sensory: str = Field(...)
    type: str = Field(...)
    neighbors: dict[str, str] = Field(default_factory=dict)
