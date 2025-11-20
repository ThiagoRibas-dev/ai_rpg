from typing import List, Dict, Any
from pydantic import BaseModel, Field
from app.tools.schemas import LocationCreate, MemoryUpsert, NpcSpawn

class CharacterExtraction(BaseModel):
    """
    Structure for extracting character details from raw text.
    """
    name: str = Field(..., description="Name of the protagonist.")
    visual_description: str = Field(..., description="Physical appearance.")
    bio: str = Field(..., description="Short backstory/biography.")
    
    # We ask for a flat dict of stats; Python will map them to the Template later
    suggested_stats: Dict[str, Any] = Field(
        ..., 
        description="Key-value pairs of attributes/skills inferred from text (e.g. {'Strength': 18, 'Agility': 'd6'})."
    )
    inventory: List[str] = Field(
        default_factory=list, 
        description="List of starting items inferred from the description."
    )
    
    # Advanced: Sidekicks/Pets defined in the bio
    companions: List[NpcSpawn] = Field(
        default_factory=list, 
        description="Familiars, pets, or followers mentioned in the text."
    )

class WorldExtraction(BaseModel):
    """
    Structure for extracting world details from raw text.
    """
    starting_location: LocationCreate = Field(..., description="The initial scene location.")
    lore: List[MemoryUpsert] = Field(
        ..., 
        description="Key facts about the world mentioned in the text (e.g. factions, history)."
    )
    initial_npcs: List[NpcSpawn] = Field(
        default_factory=list, 
        description="NPCs present in the starting scene (enemies, quest givers)."
    )
