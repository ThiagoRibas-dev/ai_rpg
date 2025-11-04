from pydantic import Field
from typing import List, Optional

from .character_core import (
    CharacterVitals,
    CharacterCombatStats,
    CharacterAbilities,
    CharacterSkillsAndTricks,
    CharacterFeats,
    CharacterClassDetails,
    CharacterMagic,
    Inventory,
)
from .base import SchemaModel
    
class PlotHook(SchemaModel):
    """Represents a single, actionable plot hook."""
    hook_title: str = Field(..., description="A short, catchy title for the plot hook.")
    description: str = Field("", description="A detailed description of the plot hook and what it involves.")
    relevant_npcs: List[str] = Field(default_factory=list, description="A list of NPC names relevant to this plot hook that the player may or may not know.")

class CharacterBrief(SchemaModel):
    """Defines the narrative elements of a player character."""
    summary: str = Field(..., description="A narrative summary of the character.")
    backstory: str = Field(..., description="Key events and defining moments of the character's life.")
    personality: str = Field(..., description="Core values, flaws, and ambitions.")
    goals: List[str] = Field(..., description="A list of the character's short-term and long-term objectives.")
    alignment: str = Field(..., description="The character's moral and ethical alignment (e.g., 'Lawful Good', 'Chaotic Evil').")
    age: int = Field(..., description="The character's age in years.")
    deity: str = Field(..., description="The character's chosen deity or philosophical belief, if any.")
    gender: str = Field(..., description="The character's gender, if applicable.")
    misc_notes: str = Field(..., description="Miscelaneous, generic notes about the character.")

class Faction(SchemaModel):
    """Represents a major faction in the world."""
    name: str = Field(..., description="The name of the faction.")
    description: str = Field(..., description="A brief description of the faction's history and nature.")
    goals: List[str] = Field(..., description="The primary goals of the faction.")
    plot_hooks: List[PlotHook] = Field(..., description="A list of possible plothooks related to this faction.")

class Month(SchemaModel):
    """Represents a month in the in-game calendar."""
    name: str = Field(..., description="The name of the month (e.g., 'January', 'Deepwinter').")
    days: int = Field(..., description="The number of days in this month.")

class DayOfWeek(SchemaModel):
    """Represents a day of the week in the in-game calendar."""
    name: str = Field(..., description="The name of the day (e.g., 'Monday', 'Moonday').")

class GameCalendar(SchemaModel):
    """Defines the structure of the in-game calendar."""
    year_length_days: int = Field(..., description="The total number of days in a year.")
    months: List[Month] = Field(..., description="A list of Month objects defining the months in the year.")
    days_of_week: List[DayOfWeek] = Field(..., description="A list of DayOfWeek objects defining the days of the week.")

class Location(SchemaModel):
    """Represents a geographical location within the campaign world."""
    name: str = Field(..., description="The name of the location.")
    location_type: str = Field(..., description="The type of location (e.g., 'Kingdom', 'City', 'Ruin', 'Landmark').")
    description: str = Field(..., description="A brief description of the location.")
    plot_hooks: List[PlotHook] = Field(..., description="A list of possible plothooks related to this location.")

class WorldState(SchemaModel):
    """Describes the foundational, enduring elements of the campaign setting."""
    setting_name: str = Field(..., description="The name of the world, region, or city.")
    description: str = Field(..., description="A high-level overview of the world's history, geography, and core concepts.")
    tone_keywords: List[str] = Field(..., description="Keywords describing the campaign's tone.")
    theme_keywords: List[str] = Field(..., description="Keywords describing the campaign's themes.")
    content_boundaries: List[str] = Field(..., description="A list of subjects or themes to be avoided.")
    major_factions: List[Faction] = Field(..., description="A list of the key powers (kingdoms, guilds, organizations).")
    locations: List[Location] = Field(..., description="A list of key locations in the world.")
    game_calendar: GameCalendar = Field(..., description="The custom calendar for this game world.")

class Quest(SchemaModel):
    """Represents a quest with stages and potential rewards."""
    quest_title: str = Field(..., description="The title of the quest.")
    description: str = Field(..., description="A detailed description of the quest, including its premise and initial objectives.")
    stages: List[str] = Field(..., description="A list of key stages or milestones for the quest.")
    rewards: List[str] = Field(..., description="Potential rewards for completing the quest.")
    relevant_npcs: List[str] = Field(..., description="NPCs directly involved in this quest.")
    related_locations: List[str] = Field(..., description="Locations related to this quest.") # Added this field based on previous plan

class Quests(SchemaModel):
    """A container for a list of quests."""
    main_quest: Optional[Quest] = Field(None, description="The primary overarching quest of the campaign.")
    secondary_quests: List[Quest] = Field(default_factory=list, description="A list of secondary quests.")

class PlayerCharacterSheet(SchemaModel):
    """The complete, detailed mechanical data for a player character."""
    entity_id: str = Field("", description="A unique identifier for this character.")
    vitals: CharacterVitals = Field(default_factory=lambda: CharacterVitals(), description="The character's core identifying information.")
    combat_stats: CharacterCombatStats = Field(default_factory=CharacterCombatStats, description="The character's combat-related statistics.")
    abilities: CharacterAbilities = Field(default_factory=lambda: CharacterAbilities(), description="The character's ability scores and saving throws.")
    skills_and_tricks: CharacterSkillsAndTricks = Field(default_factory=CharacterSkillsAndTricks, description="The character's skills and skill tricks.")
    
    feats: CharacterFeats = Field(default_factory=lambda: CharacterFeats(), description="The character's feats.")
    class_details: CharacterClassDetails = Field(default_factory=CharacterClassDetails, description="The character's class and level progression.")
    magic: CharacterMagic = Field(default_factory=lambda: CharacterMagic(), description="The character's magical and psionic abilities.")
    inventory: Inventory = Field(default_factory=lambda: Inventory(), description="The character's inventory and equipped items.")

class Relationship(SchemaModel):
    """Defines a directed relationship between two entities."""
    source: str = Field(..., description="The name of the character initiating the relationship.")
    target: str = Field(..., description="The name of the character receiving the relationship.")
    relationship_types: List[str] = Field("", description="The nature of the relationship (e.g., 'ally', 'enemy', 'mentor', 'rival', 'cohort', 'lover', etc).")
    description: str = Field("", description="A description of the relationship (e.g., 'Childhood Friend', 'Sworn Enemy').")
    strength: int = Field(0, description="The strength or intensity of the relationship (-100 to 100).")

class RelationshipMap(SchemaModel):
    """A container for the list of all relationships."""
    relationships: List[Relationship] = Field(default_factory=list, description="A list of all relationships between entities in the campaign.")

class JitCcItem(SchemaModel):
    """Represents a single potential compendium item identified for Just-In-Time Content Creation (JIT-CC)."""
    name: str = Field(..., description="The name of the item to check (e.g., 'Chronomancer', 'Aasimar').")
    type: str = Field(..., description="The type of compendium item (e.g., 'class', 'race', 'feat').")

class JitCcCheckResponse(SchemaModel):
    """The expected response from the LLM when checking for JIT-CC items."""
    items_to_check: List[JitCcItem] = Field(default_factory=list, description="A list of potential compendium items to verify.")
