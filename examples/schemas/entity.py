from pydantic import Field
from typing import List, Optional
from .character_core import (
    HitPoints,
    PlayerArmorClass,
    CombatStats,
    PlayerAbilityScores,
    PlayerSavingThrows,
    Movement,
    ClassProgressionEntry,
    SkillEntry,
)
from .base import SchemaModel

class Position(SchemaModel):
    """Represents an entity's position in the world."""
    x: int = Field(description="X coordinate.")
    y: int = Field(description="Y coordinate.")

class NPC(SchemaModel):
    """Represents a Non-Player Character or Monster using the unified core schemas."""
    entity_id: str = Field(description="A unique identifier for this specific NPC instance (e.g., 'goblin_1').")
    name: str = Field(description="The common name of the creature (e.g., 'Goblin', 'Orc Warrior').")
    alignment: str = Field(description="Creature's typical alignment.")
    size: str = Field(description="Creature's size (e.g., 'Medium', 'Large').")
    type: str = Field(description="Creature's type (e.g., 'Humanoid (Orc)', 'Animal').")
    age_category: str = Field(description="Creature's Age Category (Young, Juvenile, etc).")
    challenge_rating: float = Field(description="Challenge Rating (e.g., 1, 0.5).")

    age: int = Field(description="Creature's numeric age.")
    gender: Optional[str] = Field(description="Creature's gender when appropriate. Creatures like Ozes, some Aberrations, etcm don't have traditional genders or have a gender at all.")
    
    # Core Unified Stats
    hit_points: HitPoints = Field(..., description="The NPC's hit points information.")
    armor_class: PlayerArmorClass = Field(..., description="The NPC's Armor Class details.")
    combat: CombatStats = Field(..., description="The NPC's combat statistics.")
    abilities: PlayerAbilityScores = Field(..., description="The NPC's ability scores.")
    saving_throws: PlayerSavingThrows = Field(..., description="The NPC's saving throws.")
    movement: Movement = Field(..., description="The NPC's movement speeds.")
    
    # Simplified fields from the old schema
    special_attacks: List[str] = Field(default_factory=list, description="List of special attacks.")
    special_qualities: List[str] = Field(default_factory=list, description="List of special qualities.")
    skills: List[SkillEntry] = Field(default_factory=list, description="A list of the creature's skills and their modifiers.")
    feats: List[str] = Field(default_factory=list, description="List of feats.")
    
    # Descriptive fields
    environment: str = Field(description="Typical environment where the creature is found.")
    organization: str = Field(description="Description of typical group organization.")
    treasure: str = Field(description="Description of the creature's treasure.")
    advancement: str = Field(description="How the creature typically advances (e.g., 'By character class').")
    
    # Optional detailed fields for more complex NPCs
    class_progression: List[ClassProgressionEntry] = Field(default_factory=list, description="A list detailing the NPC's class levels or Racial Hit Dice (RHD), if any.")
    
    position: Position = Field(description="The current position of the NPC in the world.")

class NPCList(SchemaModel):
    """A wrapper to ensure the LLM returns a list of NPCs."""
    companions: Optional[List[NPC]] = Field(None, description="A list of companions, familiars, or other NPCs.")
