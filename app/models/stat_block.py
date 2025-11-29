"""
Models for the Refined StatBlock Template.
Rich, functional descriptions embedded in fields to guide LLM extraction.
"""

from typing import List, Optional, Literal, Union
from pydantic import BaseModel, Field


class IdentityDef(BaseModel):
    """Defines a category of identity."""
    description: Optional[str] = Field(None, description="Explain what this identity category represents in the game world.")
    allow_multiple: bool = Field(False, description="Set to True if a character can hold multiple values for this category simultaneously.")
    value_type: Literal["selection", "text"] = Field("selection", description="Select 'selection' if the player chooses from a defined list, or 'text' if they write a freeform description.")


class FundamentalStatDef(BaseModel):
    """The raw inputs for the system's math (Attributes)."""
    abbr: Optional[str] = Field(None, description="The standard abbreviation used for this stat.")
    description: Optional[str] = Field(None, description="Explain what aspect of the character this stat measures.")
    data_type: Literal["integer", "die_code", "dots", "float"] = Field("integer", description="The numerical format used to track this stat.")
    default: Union[int, str, float] = Field(10, description="The starting value assigned to an average character.")


class VitalResourceDef(BaseModel):
    """Meters that determine life, death, or sanity."""
    type: Literal["depleting", "accumulating"] = Field("depleting", description="Select 'depleting' if it counts down (like HP), or 'accumulating' if it counts up (like Stress).")
    min_value: int = 0
    max_formula: Optional[str] = Field(None, description="Formula to calculate the maximum capacity of this resource. Use '0' if static.")
    on_zero: Optional[str] = Field(None, description="The consequence applied when this resource reaches the minimum value.")
    on_max: Optional[str] = Field(None, description="The consequence applied when this resource reaches its maximum value.")


class ConsumableResourceDef(BaseModel):
    """Fuel for abilities that refills over time."""
    reset_trigger: str = Field("Rest", description="The event or condition that replenishes this resource.")
    max_formula: Optional[str] = Field(None, description="Formula to calculate the maximum capacity of this resource.")


class SkillDef(BaseModel):
    """Learned proficiencies."""
    linked_stat: Optional[str] = Field(None, description="The Fundamental Stat that modifies this skill.")
    can_be_untrained: bool = Field(True, description="Set to True if this skill can be used without specific training.")

SkillValue = Union[str, SkillDef]


class FeatureContainerDef(BaseModel):
    """Buckets for special abilities (Feats, Spells, Edges)."""
    description: Optional[str] = Field(None, description="Explain what type of abilities or traits belong in this container.")


class EquipmentConfig(BaseModel):
    """Inventory definition."""
    capacity_stat: Optional[str] = Field(None, description="The stat or formula that determines how much a character can carry.")
    slots: dict[str, List[str]] = Field(
        default_factory=dict, 
        description="A dictionary mapping body slot names to the types of items they accept."
    )


class StatBlockTemplate(BaseModel):
    """
    The blueprint for an Entity.
    Populate these dictionaries based on the Game Rules text.
    """
    template_name: str = Field(..., description="The official name of this character sheet template.")
    
    identity_categories: dict[str, IdentityDef] = Field(
        default_factory=dict,
        description="The set of categorical traits that define a character's background (e.g. Race, Class)."
    )
    fundamental_stats: dict[str, FundamentalStatDef] = Field(
        default_factory=dict,
        description="The set of raw attributes that serve as inputs for game math (e.g. Strength, Agility)."
    )
    
    derived_stats: dict[str, str] = Field(
        default_factory=dict,
        description="The set of read-only values calculated from Fundamental Stats (e.g. AC, Initiative)."
    )
    
    vital_resources: dict[str, VitalResourceDef] = Field(
        default_factory=dict,
        description="The set of meters that determine character survival or sanity (e.g. HP, Stress)."
    )
    consumable_resources: dict[str, ConsumableResourceDef] = Field(
        default_factory=dict,
        description="The set of expendable resources used to power abilities (e.g. Mana, Ammo)."
    )
    
    skills: dict[str, SkillValue] = Field(
        default_factory=dict,
        description="The complete list of proficiencies available in the game."
    )
    features: dict[str, FeatureContainerDef] = Field(
        default_factory=dict,
        description="The categories of special abilities a character can acquire."
    )
    
    equipment: EquipmentConfig = Field(default_factory=EquipmentConfig)
