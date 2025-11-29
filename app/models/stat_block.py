"""
Models for the Refined StatBlock Template.
Implements granular categorization for Identity, Equipment, and Resources.
"""

from typing import List, Optional, Literal, Union
from pydantic import BaseModel, Field


class IdentityDef(BaseModel):
    """
    Defines a category of identity.
    e.g. "Species" (Race), "Profession" (Class), "Background".
    """
    category_name: str = Field(..., description="e.g. 'Race', 'Playbook', 'Background'")
    description: Optional[str] = None
    allow_multiple: bool = Field(False, description="Can you have two of these? (e.g. Multiclassing)")
    # TWEAK: Distinguish between selecting from a list (Class) vs writing free text (Beliefs/Instincts)
    value_type: Literal["selection", "text"] = Field("selection", description="Is this a specific option or free text?")


class FundamentalStatDef(BaseModel):
    """
    BASE ATTRIBUTES. The raw inputs for the system's math.
    e.g. Strength, Agility, Logic.
    """
    name: str
    abbr: Optional[str] = None
    description: Optional[str] = None
    data_type: Literal["integer", "die_code", "dots", "float"] = "integer"
    default: Union[int, str, float] = 10


class DerivedStatDef(BaseModel):
    """
    CALCULATED VALUES. Read-only outputs.
    e.g. AC, Initiative, Save DC.
    """
    name: str
    formula: str = Field(..., description="Python math string.")


class VitalResourceDef(BaseModel):
    """
    LIFE METERS.
    If this runs out (or fills up), the character dies, goes mad, or is taken out.
    e.g. HP, Sanity, Stress.
    """
    name: str
    type: Literal["depleting", "accumulating"] = "depleting"
    min_value: int = 0
    max_formula: Optional[str] = Field(None, description="Formula for max value.")
    on_zero: Optional[str] = Field(None, description="Effect at 0 (e.g. 'Death').")
    on_max: Optional[str] = Field(None, description="Effect at max (e.g. 'Panic').")


class ConsumableResourceDef(BaseModel):
    """
    FUEL / EXPANDABLES.
    Spent to use abilities. Reloaded via rest/actions.
    e.g. Spell Slots, Ki, Ammo, Power Points.
    """
    name: str
    reset_trigger: str = Field("Rest", description="When does this refill?")
    max_formula: Optional[str] = Field(None, description="Formula for max capacity.")


class SkillDef(BaseModel):
    """
    LEARNED PROFICIENCIES.
    """
    name: str
    linked_stat: Optional[str] = Field(None, description="Associated Fundamental Stat.")
    can_be_untrained: bool = True


class FeatureContainerDef(BaseModel):
    """
    Buckets for special abilities.
    e.g. "Feats", "Class Features", "Spells Known".
    """
    name: str
    description: Optional[str] = None


class BodySlotDef(BaseModel):
    """
    A specific location on the body to equip items.
    e.g. 'Main Hand', 'Off Hand', 'Ring 1', 'Ring 2'.
    """
    name: str
    description: Optional[str] = None
    accepted_item_types: List[str] = Field(default_factory=list, description="e.g. ['Ring'], ['Weapon', 'Shield']")


class EquipmentConfig(BaseModel):
    """
    Inventory definition.
    """
    capacity_stat: Optional[str] = Field(None, description="CalculatedStat defining carry limit.")
    slots: List[BodySlotDef] = Field(default_factory=list)


class StatBlockTemplate(BaseModel):
    """
    The blueprint for an Entity.
    """
    template_name: str
    
    identity_categories: List[IdentityDef] = Field(default_factory=list)
    fundamental_stats: List[FundamentalStatDef] = Field(default_factory=list)
    derived_stats: List[DerivedStatDef] = Field(default_factory=list)
    
    vital_resources: List[VitalResourceDef] = Field(default_factory=list)
    consumable_resources: List[ConsumableResourceDef] = Field(default_factory=list)
    
    skills: List[SkillDef] = Field(default_factory=list)
    features: List[FeatureContainerDef] = Field(default_factory=list)
    
    equipment: EquipmentConfig = Field(default_factory=EquipmentConfig)
