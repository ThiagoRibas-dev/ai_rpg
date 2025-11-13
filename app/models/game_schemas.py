"""
Pydantic models for rich game system templates.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal


class AttributeDefinition(BaseModel):
    """Character ability scores (STR, DEX, INT, etc.)"""
    name: str
    abbreviation: Optional[str] = None
    description: str  # REQUIRED: Concise description
    default: int | float
    range: Optional[List[int | float]] = None  # [min, max]
    modifier_formula: Optional[str] = None
    applies_to: List[str] = Field(default_factory=list)
    icon: Optional[str] = None


class ResourceDefinition(BaseModel):
    """Expendable/trackable resources (HP, Mana, Sanity, etc.)"""
    name: str
    description: str  # REQUIRED: Concise description
    base_formula: Optional[str] = None
    default: int | float = 0
    min: int | float = 0
    has_max: bool = True
    max_formula: Optional[str] = None
    regenerates: bool = False
    regeneration_rate: Optional[int | float] = None
    death_at: Optional[int | float] = None
    icon: Optional[str] = None


class DerivedStatDefinition(BaseModel):
    """Calculated stats (AC, saves, initiative, etc.)"""
    name: str
    description: str  # REQUIRED: Concise description
    formula: str
    default: int | float = 0
    icon: Optional[str] = None


class EntitySchema(BaseModel):
    """Schema for a type of game entity (character, item, location, etc.)"""
    attributes: List[AttributeDefinition] = Field(default_factory=list)
    resources: List[ResourceDefinition] = Field(default_factory=list)
    derived_stats: List[DerivedStatDefinition] = Field(default_factory=list)


class SkillDefinition(BaseModel):
    """Learned abilities (skills, moves, actions, etc.)"""
    name: str
    description: str  # REQUIRED: Concise description
    system_type: Literal["ranked", "percentile", "dice_pool", "binary", "die_type"] = "ranked"
    default_value: int | str = 0
    max_value: Optional[int] = None
    linked_attribute: Optional[str] = None
    class_skill_for: List[str] = Field(default_factory=list)
    icon: Optional[str] = None


class ActionType(BaseModel):
    """A specific type of action available in combat"""
    name: str
    description: str  # REQUIRED: Concise description
    quantity_per_turn: int | str
    timing: Literal["your_turn", "others_turn", "any_turn", "out_of_turn_order"] = "your_turn"
    is_reactive: bool = False
    examples: List[str] = Field(default_factory=list)
    special_rules: List[str] = Field(default_factory=list)
    can_downgrade_to: List[str] = Field(default_factory=list)


class ActionEconomyDefinition(BaseModel):
    """How actions work in combat"""
    name: str = "Action Economy"
    system_type: Literal["fixed_types", "action_points", "multi_action", "narrative"] = "fixed_types"
    action_types: List[ActionType] = Field(default_factory=list)
    points_per_turn: Optional[int] = None
    point_costs: Optional[Dict[str, int]] = None
    multi_action_penalty: Optional[str] = None
    narrative_guidance: Optional[str] = None
    description: str = ""
    special_rules: List[str] = Field(default_factory=list)


class RuleSchema(BaseModel):
    """A game rule or mechanic"""
    name: str
    type: Literal["resolution", "calculation", "mechanic", "movement", "combat"] = "mechanic"
    formula: Optional[str] = None
    description: str  # REQUIRED: Concise description
    examples: List[str] = Field(default_factory=list)


class ConditionDefinition(BaseModel):
    """Status effects and conditions (Blinded, Stunned, etc.)"""
    name: str
    description: str  # REQUIRED: Concise description
    effects: List[str]
    duration: Optional[str] = None
    icon: Optional[str] = None


class ClassDefinition(BaseModel):
    """Character class/archetype (optional)"""
    name: str
    description: str  # REQUIRED: Concise description
    hit_die: Optional[str] = None
    primary_attributes: List[str] = Field(default_factory=list)
    special_abilities: List[str] = Field(default_factory=list)


class RaceDefinition(BaseModel):
    """Character race/species (optional)"""
    name: str
    description: str  # REQUIRED: Concise description
    ability_modifiers: List[Dict[str, int]] = Field(default_factory=list)
    special_qualities: List[str] = Field(default_factory=list)
    size: Optional[str] = None
    speed: Optional[int] = None


class GameTemplate(BaseModel):
    """Complete game system template"""
    genre: Dict[str, Any]
    tone: Dict[str, Any]
    
    entity_schemas: Dict[str, EntitySchema] = Field(
        default_factory=lambda: {"character": EntitySchema()}
    )
    
    rule_schemas: List[RuleSchema] = Field(default_factory=list)
    conditions: List[ConditionDefinition] = Field(default_factory=list)
    skills: List[SkillDefinition] = Field(default_factory=list)
    action_economy: Optional[ActionEconomyDefinition] = None
    
    classes: List[ClassDefinition] = Field(default_factory=list)
    races: List[RaceDefinition] = Field(default_factory=list)


# NEW: Pydantic models to wrap lists for structured LLM output

class SkillList(BaseModel):
    """A list of skills."""
    skills: List[SkillDefinition] = Field(default_factory=list)

class ConditionList(BaseModel):
    """A list of conditions."""
    conditions: List[ConditionDefinition] = Field(default_factory=list)

class ClassList(BaseModel):
    """A list of classes."""
    classes: List[ClassDefinition] = Field(default_factory=list)

class RaceList(BaseModel):
    """A list of races."""
    races: List[RaceDefinition] = Field(default_factory=list)
