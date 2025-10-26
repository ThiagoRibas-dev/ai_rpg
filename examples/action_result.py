from pydantic import Field
from typing import List, Optional
from enum import Enum
from .entity import NPC
from .campaign_schemas import Relationship
from app.schemas.session_schemas import GameMode
from .base import SchemaModel

class OperationType(str, Enum):
    """Defines the types of atomic operations the LLM can request."""
    ROLL_SKILL_CHECK = "roll_skill_check"
    ROLL_ATTACK = "roll_attack"
    SPAWN_NPC = "spawn_npc"
    ADD_QUEST = "add_quest"
    UPDATE_QUEST = "update_quest"
    UPDATE_LOCATION = "update_location"
    ADD_RELATIONSHIP = "add_relationship"
    UPDATE_RELATIONSHIP = "update_relationship"
    CHANGE_GAME_MODE = "change_game_mode"
    INITIATE_COMBAT = "initiate_combat"
    END_COMBAT = "end_combat"
    INITIATE_GRAPPLE = "initiate_grapple" # Placeholder for complex actions
    REQUEST_ENTITY_DETAILS = "request_entity_details" # For dynamic info retrieval
    REQUEST_SPELL_DETAILS = "request_spell_details" # For dynamic info retrieval

class Operation(SchemaModel):
    """
    A single, atomic operation to be executed by the game engine.
    All fields are optional because only the relevant fields for a given 'type' will be populated.
    """
    type: OperationType = Field(description="The type of operation to perform.")
    
    # --- Fields for 'roll_skill_check' operation ---
    skill_name: Optional[str] = Field(None, description="The name of the skill to check (e.g., 'Perception', 'Diplomacy').")
    dc: Optional[int] = Field(None, description="The Difficulty Class (DC) for the skill check.")
    
    # --- Fields for 'roll_attack' operation ---
    attacker_id: Optional[str] = Field(None, description="The entity_id of the attacking combatant.")
    target_id: Optional[str] = Field(None, description="The entity_id of the target combatant.")
    base_damage: Optional[str] = Field(None, description="The base damage dice notation (e.g., '1d6', '2d8+2').")

    # --- Fields for 'spawn_npc' operation ---
    npc_data: Optional[NPC] = Field(None, description="The full NPC schema to be spawned into the game.")

    # --- Fields for 'add_quest' operation ---
    quest_title: Optional[str] = Field(None, description="The title of the new quest.")
    quest_description: Optional[str] = Field(None, description="A detailed description of the new quest.")
    quest_stages: Optional[List[str]] = Field(None, description="A list of key stages or milestones for the new quest.")
    quest_rewards: Optional[List[str]] = Field(None, description="Potential rewards for completing the new quest.")
    quest_relevant_npcs: Optional[List[str]] = Field(None, description="NPCs directly involved in the new quest.")

    # --- Fields for 'update_quest' operation ---
    quest_title_to_update: Optional[str] = Field(None, description="The title of the quest to be updated.")
    new_stage: Optional[str] = Field(None, description="A new stage to add to the specified quest.")

    # --- Fields for 'update_location' operation ---
    new_location: Optional[str] = Field(None, description="The ID of the new location to transition to.")

    # --- Fields for 'add_relationship' operation ---
    relationship: Optional[Relationship] = Field(None, description="The full Relationship schema to be added.")

    # --- Fields for 'update_relationship' operation ---
    source: Optional[str] = Field(None, description="The entity_id of the source character in the relationship.")
    target: Optional[str] = Field(None, description="The entity_id of the target character in the relationship.")
    new_description: Optional[str] = Field(None, description="The updated description for the relationship.")

    # --- Fields for 'change_game_mode' operation ---
    game_mode: Optional[GameMode] = Field(None, description="The new GameMode to transition to (ENCOUNTER, EXPLORATION, or DOWNTIME).")

    # --- Fields for 'request_entity_details' / 'request_spell_details' operations ---
    entity_id: Optional[str] = Field(None, description="The entity_id of the character or NPC whose details are requested.")
    requested_fields: Optional[List[str]] = Field(None, description="A list of specific fields to retrieve from the entity's sheet (e.g., ['feats', 'inventory']).")
    spell_name: Optional[str] = Field(None, description="The name of the spell whose details are requested.")

    class Config:
        """Pydantic config to ensure descriptions are added to the schema."""
        json_schema_extra = {
            "description": "A single, atomic operation to be executed by the game engine. All fields are optional because only the relevant fields for a given 'type' will be populated."
        }

class ExecuteTurn(SchemaModel):
    """
    The primary response model for the LLM, representing a sequence of operations
    to be executed by the game engine, along with a final narrative.
    """
    narrative: str = Field(description="The overarching narrative containing the outcome of the turn.")
    operations: List[Operation] = Field(
        description="A list of atomic operations for the game engine to execute. "
                    "Each operation is an 'Operation' object with a 'type' and relevant optional fields."
    )
    suggestions: List[str] = Field(None, description="A list of suggested player actions for the next turn.")
