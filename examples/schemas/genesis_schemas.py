from pydantic import Field
from typing import List, Optional
from app.schemas.campaign_schemas import (
    WorldState,
    CharacterBrief,
    PlayerCharacterSheet,
    Quests,
    RelationshipMap,
)
from app.schemas.character_core import CharacterContentCheckResult
from app.schemas.entity import NPC
from .base import SchemaModel

class CampaignContext(SchemaModel):
    player_character_sheet: PlayerCharacterSheet = Field(default_factory=lambda: PlayerCharacterSheet())
    world_state: Optional[WorldState] = None
    character_brief: Optional[CharacterBrief] = None
    content_check: Optional[CharacterContentCheckResult] = None
    companions: List[NPC] = Field(default_factory=list)
    relationship_map: Optional[RelationshipMap] = None
    quests: Optional[Quests] = None
