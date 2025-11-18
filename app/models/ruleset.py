"""
Models for the Static Ruleset (Game System).
These define the 'physics' and 'library' of the game world.
"""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class RuleEntry(BaseModel):
    """A specific rule definition (e.g., 'Grappling', 'Illumination')."""
    name: str
    text: str
    tags: List[str] = Field(default_factory=list)


class SkillDef(BaseModel):
    """Definition of a skill available in the system."""
    name: str
    description: str
    linked_ability: Optional[str] = None  # e.g., "Dexterity"


class ConditionDef(BaseModel):
    """Definition of a status effect."""
    name: str
    description: str
    effects: List[str] = Field(default_factory=list)


class FeatureDef(BaseModel):
    """
    Generic definition for selectable features.
    Used for Feats, Spells, Cyberware, Edges, etc.
    """
    name: str
    description: str
    cost: Optional[str] = None  # e.g., "2 MP", "1 Slot"
    prerequisites: Optional[str] = None


class Compendium(BaseModel):
    """The Global Library of the game."""
    skills: List[SkillDef] = Field(default_factory=list)
    conditions: List[ConditionDef] = Field(default_factory=list)
    damage_types: List[str] = Field(default_factory=list)
    
    # Flexible dictionaries for things like "Spells", "Feats", "Cyberware"
    # Key = Category Name (e.g., "Level 1 Spells"), Value = List of Features
    features: Dict[str, List[FeatureDef]] = Field(default_factory=dict)
    
    # Simple items list for now, can be expanded
    items: List[FeatureDef] = Field(default_factory=list)


class Ruleset(BaseModel):
    """The Root Object for a Game System."""
    meta: Dict[str, str] = Field(default_factory=lambda: {"name": "Untitled System"})
    
    resolution_mechanic: str = Field(..., description="The core dice mechanic string.")
    
    # Static Rules
    tactical_rules: List[RuleEntry] = Field(default_factory=list)
    exploration_rules: List[RuleEntry] = Field(default_factory=list)
    
    compendium: Compendium = Field(default_factory=Compendium)
