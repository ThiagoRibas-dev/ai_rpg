from pydantic import Field
from typing import List, Optional, Union
from enum import Enum
from app.schemas.entity import Position
from .base import SchemaModel

class GameMode(str, Enum):
    ENCOUNTER = "ENCOUNTER"
    EXPLORATION = "EXPLORATION"
    DOWNTIME = "DOWNTIME"

class GameDateTime(SchemaModel):
    """Represents a specific point in time using the world's calendar."""
    year: int = Field(1, description="The current year.")
    month_index: int = Field(0, description="The 0-based index of the current month in the GameCalendar.months list.")
    day_of_month: int = Field(1, description="The 1-based day of the current month.")
    hour: int = Field(8, description="The current hour (0-23).")
    minute: int = Field(0, description="The current minute (0-59).")

class ActiveEffect(SchemaModel):
    """A temporary effect or condition on an entity."""
    name: str = Field(..., description="Name of the effect (e.g., 'Bless', 'Rage').")
    duration_rounds: Optional[int] = Field(None, description="Remaining duration in combat rounds.")
    description: str = Field(..., description="Mechanical and narrative effect.")

class UsedResource(SchemaModel):
    """A generic model to track usage of limited resources."""
    id: str = Field(..., description="Identifier of the resource (e.g., 'spell_slot_1', 'maneuver_crusaders_strike').")
    count: int = Field(1, description="How many times this resource has been used.")

class EntityDynamicState(SchemaModel):
    """Tracks the dynamic state of a single entity in the scene."""
    entity_id: str = Field(..., description="The ID of the entity this state applies to.")
    current_hp: int = Field(..., description="The entity's current hit points.")
    temporary_hp: int = Field(0, description="The entity's temporary hit points.")
    position: Position = Field(..., description="The entity's current position in the world.")
    active_effects: List[ActiveEffect] = Field(default_factory=list, description="A list of active temporary effects or conditions on the entity.")

# --- Mode-Specific States ---

class CombatEnvironment(SchemaModel):
    """Describes the environmental conditions of a combat scene."""
    terrain: str = Field("plains", description="Type of terrain (e.g., 'forest', 'dungeon', 'city street').")
    lighting: str = Field("bright", description="Lighting conditions (e.g., 'bright', 'dim', 'darkness').")
    cover: List[str] = Field(default_factory=list, description="Available sources of cover.")
    hazards: List[str] = Field(default_factory=list, description="Environmental hazards present.")

class CombatActionLog(SchemaModel):
    """A log of a single action taken in combat."""
    actor_id: str = Field(..., description="The ID of the entity that took the action.")
    action_type: str = Field(..., description="The type of action (e.g., 'Attack', 'Cast Spell', 'Move').")
    target_id: Optional[str] = Field(None, description="The ID of the target, if any.")
    details: str = Field(..., description="A narrative description of the action and its outcome.")

class LocationDetails(SchemaModel):
    """Detailed features of an exploration location."""
    architecture: str = Field("unknown", description="The architectural style of the location.")
    atmosphere: str = Field("calm", description="The general atmosphere or mood of the location.")
    key_features: List[str] = Field(default_factory=list, description="A list of key features or landmarks.")

class NearbyNPC(SchemaModel):
    """A summary of an NPC in the immediate vicinity."""
    entity_id: str = Field(..., description="The ID of the NPC.")
    name: str = Field(..., description="The name of the NPC.")
    observation: str = Field(..., description="A brief observation of what the NPC is doing.")

class GeneralDowntime(SchemaModel):
    """Details for a general or unspecified downtime activity."""
    description: str = Field("Passing the time.", description="A description of the general downtime activity.")

class Combatant(SchemaModel):
    """Represents an entity participating in combat with dynamic state."""
    entity_id: str = Field(..., description="The unique identifier for this combatant.")
    name: str = Field(..., description="The name of the combatant.")
    type: str = Field(..., description="The type of combatant (e.g., 'PC', 'Monster', 'NPC').")
    current_hp: int = Field(..., description="The combatant's current hit points.")
    max_hp: int = Field(..., description="The combatant's maximum hit points.")
    ac: int = Field(..., description="The combatant's Armor Class.")
    position: Position = Field(..., description="The combatant's current position in the combat scene.")
    status_effects: List[str] = Field(default_factory=list, description="A list of active status effects on the combatant.")
    # Add other combat-relevant fields as needed, e.g., spells_prepared, actions

class CombatState(SchemaModel):
    """Tracks the state of a combat encounter."""
    round_number: int = Field(0, description="The current combat round number.")
    turn_number: int = Field(0, description="The current turn number within the round.")
    active_actor_id: Optional[str] = Field(None, description="The entity_id of the combatant whose turn it currently is.")
    initiative_order: List[str] = Field(default_factory=list, description="A list of entity_ids sorted by initiative, determining turn order.")
    party: List[Combatant] = Field(default_factory=list, description="A list of player characters and their allies in combat.")
    enemies: List[Combatant] = Field(default_factory=list, description="A list of enemy NPCs/monsters in combat.")
    environment: CombatEnvironment = Field(default_factory=CombatEnvironment, description="Details about the combat environment (e.g., terrain, lighting, cover, hazards).")
    story_flags: List[str] = Field(default_factory=list, description="Flags related to the combat narrative or specific conditions.")
    recent_actions: List[CombatActionLog] = Field(default_factory=list, description="A log of recent actions taken in combat.")
    previous_location_id: Optional[str] = Field(None, description="The location ID before combat started.")

class ExplorationState(SchemaModel):
    """Tracks the state during exploration mode."""
    current_location_id: str = Field(..., description="ID of the current map or area.")
    current_scene_description: str = Field(..., description="A narrative description of the immediate surroundings.")
    location_details: LocationDetails = Field(default_factory=LocationDetails, description="Detailed features of the current location.")
    features_of_interest: List[str] = Field(default_factory=list, description="Notable features or points of interest in the scene.")
    nearby_npcs: List[NearbyNPC] = Field(default_factory=list, description="Summary of NPCs in the immediate vicinity.")
    exploration_flags: List[str] = Field(default_factory=list, description="Flags related to discoveries or ongoing exploration.")
    # Dynamic Entity States (as a list, not a dict) - for non-combat entities
    entity_states: List[EntityDynamicState] = Field(default_factory=list, description="A list of dynamic states for entities present in the current scene.")

class TravelDetails(SchemaModel):
    """Details for a travel activity during downtime."""
    start_location: str = Field(..., description="The starting location of the journey.")
    destination_location: str = Field(..., description="The intended destination of the journey.")
    distance_remaining: int = Field(..., description="The remaining distance to the destination.")
    pace: str = Field(..., description="The pace of travel (e.g., 'normal', 'forced_march', 'fast').")
    terrain: str = Field(..., description="The type of terrain being traversed (e.g., 'plains', 'forest', 'mountains').")
    travel_events: List[str] = Field(default_factory=list, description="A log of notable events that occurred during travel.")

class CraftingTask(SchemaModel):
    """Details for a crafting activity during downtime."""
    item_name: str = Field(..., description="The name of the item being crafted.")
    required_skill: str = Field(..., description="The skill required for crafting (e.g., 'Craft (Alchemy)').")
    dc: int = Field(..., description="The Difficulty Class (DC) for the crafting check.")
    time_required_hours: int = Field(..., description="The total time required to complete crafting in hours.")
    progress_hours: int = Field(0, description="The current progress made on the crafting task in hours.")
    resources_consumed: List[str] = Field(default_factory=list, description="A list of resources already consumed for crafting.")
    resources_needed: List[str] = Field(default_factory=list, description="A list of resources still needed for crafting.")

class RestingDetails(SchemaModel):
    """Details for a resting activity during downtime."""
    rest_type: str = Field(..., description="The type of rest (e.g., 'short', 'long', 'full_night').")
    duration_hours: int = Field(..., description="The duration of the rest in hours.")
    healing_gained: int = Field(0, description="Total hit points recovered during the rest.")
    spell_slots_recovered: List[str] = Field(default_factory=list, description="A list of spell slots recovered (e.g., 'cleric_level_1_slot_1').")
    watch_schedule: List[str] = Field(default_factory=list, description="A list of entity_ids indicating who is on watch during the rest.")

class DowntimeState(SchemaModel):
    """Tracks the state during downtime mode."""
    downtime_activity_type: str = Field(..., description="Type of downtime activity (e.g., 'travel', 'crafting', 'rest').")
    activity_details: Union[TravelDetails, CraftingTask, RestingDetails, GeneralDowntime] = Field(default_factory=GeneralDowntime, description="Specific details of the ongoing downtime activity.")
    downtime_flags: List[str] = Field(default_factory=list, description="Flags related to downtime activities (e.g., 'market_open', 'training_complete').")

class SessionState(SchemaModel):
    """Represents the dynamic, moment-to-moment state of a playable campaign session."""
    
    # General Info
    turn_count: int = Field(0, description="The overall turn count for the campaign.")
    current_datetime: GameDateTime = Field(..., description="The current in-game date and time.")
    game_mode: GameMode = Field(GameMode.EXPLORATION, description="The current mode of play (ENCOUNTER, EXPLORATION, or DOWNTIME).")
    active_state: Union[ExplorationState, CombatState, DowntimeState] = Field(..., description="The detailed state object for the currently active game mode.")

    # Active Quest Tracking (remains global)
    active_quest_ids: List[str] = Field(default_factory=list, description="A list of IDs for quests currently active or being pursued by the party.")

    # Player-specific resource tracking (remains global)
    player_resources_used: List[UsedResource] = Field(default_factory=list, description="A list of resources used by the player character during the session.")