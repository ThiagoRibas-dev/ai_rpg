from typing import List, Literal
from pydantic import BaseModel, Field

# NOTE: We define independent models here to avoid coupling with Tool Schemas.
# Tool Schemas have strict Literal["name"] fields which confuse the LLM during data extraction.


class NpcData(BaseModel):
    name: str = Field(..., description="Name of the NPC.")
    visual_description: str = Field(..., description="Physical appearance.")
    stat_template: str = Field(
        ..., description="Archetype (e.g. 'Guard', 'Civilian', 'Boss')."
    )
    initial_disposition: Literal["hostile", "neutral", "friendly"] = "neutral"


class LocationData(BaseModel):
    key: str = Field(..., description="Unique snake_case ID (e.g. 'loc_market').")
    name: str = Field(..., description="Display name (e.g. 'The Market').")
    description_visual: str = Field(...)
    description_sensory: str = Field(...)
    type: str = Field(..., description="indoor, outdoor, structure, etc.")


class LoreData(BaseModel):
    content: str
    tags: List[str]
    priority: int = 3
    kind: str = "lore"


class WorldExtraction(BaseModel):
    """
    Structure for extracting world details from raw text.
    """

    genre: str = Field(
        ..., description="The specific sub-genre inferred from the text."
    )
    tone: str = Field(..., description="The atmospheric tone.")

    starting_location: LocationData = Field(
        ..., description="The initial scene location."
    )
    adjacent_locations: List[LocationData] = Field(
        default_factory=list,
        description="2-3 locations directly connected to the starting location.",
    )
    lore: List[LoreData] = Field(..., description="Key facts about the world.")
    initial_npcs: List[NpcData] = Field(
        default_factory=list, description="NPCs present in the starting scene."
    )
