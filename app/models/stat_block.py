"""
Models for the StatBlock Template (Entity Structure).
These define the 'shape' of a character sheet.
"""

from typing import List, Optional, Literal, Union
from pydantic import BaseModel, Field


class AbilityDef(BaseModel):
    """
    Core attributes (STR, DEX, etc).
    Supports Integers (D&D), Die Codes (Savage Worlds), or Dots (WoD).
    """
    name: str
    abbr: Optional[str] = None
    description: Optional[str] = None
    data_type: Literal["integer", "die_code", "dots", "float", "string"] = "integer"
    default: Union[int, str, float] = 10
    
    # Validations
    range_min: Optional[float] = None
    range_max: Optional[float] = None
    allowed_values: Optional[List[str]] = None  # e.g. ["d4", "d6", "d8"]


class VitalDef(BaseModel):
    """
    Resource pools that fluctuate (HP, Mana, Sanity).
    """
    name: str
    description: Optional[str] = None
    min_value: float = 0
    has_max: bool = True
    
    # Formula to calculate max (e.g. "10 + CON_mod")
    # Evaluated by app/utils/math_engine.py
    max_formula: Optional[str] = Field(None, description="Math formula for dynamic max value (e.g. '10 + CON').")
    
    recover: Optional[str] = None  # Text description of recovery


class TrackDef(BaseModel):
    """
    Abstract progress trackers (Clocks, Experience, Stress).
    """
    name: str
    description: Optional[str] = None
    max_value: int = 4
    visual_style: Literal["clock", "bar", "dots", "checkboxes"] = "clock"
    
    # Logic hooks
    trigger_on_full: Optional[str] = None  # e.g., "Take Trauma"
    trigger_on_empty: Optional[str] = None
    reset_condition: Optional[str] = None


class SlotDef(BaseModel):
    """
    Containers for items or features (Inventory, Spell Slots, Loadout).
    """
    name: str
    description: Optional[str] = None
    
    # Capacity Logic
    capacity_formula: Optional[str] = None  # e.g. "STR * 5"
    fixed_capacity: Optional[int] = None
    
    # What can go in here?
    accepts_tags: List[str] = Field(default_factory=list)  # e.g. ["spell", "item"]
    
    # Behavior
    overflow_behavior: Literal["prevent", "penalty", "warn"] = "prevent"


class DerivedStatDef(BaseModel):
    """
    Stats calculated entirely from other values (AC, Save DC).
    """
    name: str
    formula: str = Field(..., description="Math formula using Ability names (e.g. '10 + DEX').")


class StatBlockTemplate(BaseModel):
    """
    The blueprint for a specific type of entity (e.g. 'Heroic PC', 'Goblin').
    """
    template_name: str
    
    abilities: List[AbilityDef] = Field(default_factory=list)
    vitals: List[VitalDef] = Field(default_factory=list)
    tracks: List[TrackDef] = Field(default_factory=list)
    slots: List[SlotDef] = Field(default_factory=list)
    derived_stats: List[DerivedStatDef] = Field(default_factory=list)
