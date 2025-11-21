from typing import Any, Dict, List

from pydantic import BaseModel, Field

from app.tools.schemas import LocationCreate, MemoryUpsert, NpcSpawn


class CharacterExtractionBase(BaseModel):
    """
    Base structure for character extraction.
    The 'stats' field is omitted here; it will be injected dynamically
    based on the Game System Template at runtime.
    """

    name: str = Field(..., description="Name of the protagonist.")
    visual_description: str = Field(..., description="Physical appearance.")
    bio: str = Field(..., description="Short backstory/biography.")

    inventory: List[str] = Field(
        default_factory=list,
        description="List of starting items inferred from the description.",
    )

    companions: List[NpcSpawn] = Field(
        default_factory=list,
        description="Familiars, pets, or followers mentioned in the text.",
    )


class CharacterExtraction(CharacterExtractionBase):
    """
    The legacy/fallback structure using a loose dictionary.
    Used when no specific template is available.
    """

    suggested_stats: Dict[str, Any] = Field(
        ..., description="Key-value pairs of attributes/skills inferred from text."
    )


class WorldExtraction(BaseModel):
    """
    Structure for extracting world details from raw text.
    """

    genre: str = Field(
        ...,
        description="The specific sub-genre inferred from the text (e.g. 'Cosmic Horror', 'High Fantasy').",
    )
    tone: str = Field(
        ..., description="The atmospheric tone (e.g. 'Gritty', 'Whimsical', 'Tense')."
    )

    starting_location: LocationCreate = Field(
        ..., description="The initial scene location."
    )
    lore: List[MemoryUpsert] = Field(
        ...,
        description="Key facts about the world mentioned in the text (e.g. factions, history).",
    )
    initial_npcs: List[NpcSpawn] = Field(
        default_factory=list,
        description="NPCs present in the starting scene (enemies, quest givers).",
    )
