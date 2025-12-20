from typing import Literal, Dict, Any, List, Optional
from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# PREFAB / MANIFEST EXTRACTION SCHEMAS
# ---------------------------------------------------------------------------

ValidPrefabType = Literal[
    "VAL_INT",
    "VAL_COMPOUND",
    "VAL_STEP_DIE",
    "VAL_LADDER",
    "VAL_BOOL",
    "RES_POOL",
    "RES_COUNTER",
    "RES_TRACK",
    "CONT_LIST",
    "CONT_TAGS",
    "CONT_WEIGHTED",
]

CategoryType = Literal[
    "attributes",
    "resources",
    "skills",
    "inventory",
    "features",
    "progression",
    "combat",
    "status",
    "meta",
    "identity",
    "narrative",
]


class ExtractedField(BaseModel):
    label: str
    path: str = Field(..., description="snake_case.path")
    prefab: ValidPrefabType
    category: CategoryType
    config: Dict[str, Any] = Field(default_factory=dict)
    formula: Optional[str] = None
    usage_hint: str = Field(..., description="Short explanation for the AI")

    @field_validator("prefab", mode="before")
    @classmethod
    def sanitize(cls, v):
        # Map some looser LLM outputs to real prefab IDs
        mapping = {
            "VAL_NUMBER": "VAL_INT",
            "RES_BAR": "RES_POOL",
            "VAL_DIE": "VAL_STEP_DIE",
            "CONT_ARRAY": "CONT_LIST",
        }
        return mapping.get(v, v)


class ExtractedFieldList(BaseModel):
    fields: List[ExtractedField]


class MechanicsExtraction(BaseModel):
    dice_notation: str
    resolution_mechanic: str
    success_condition: str
    crit_rules: str
    fumble_rules: str = ""
    aliases: Dict[str, str] = Field(default_factory=dict)


class ProceduresExtraction(BaseModel):
    combat: str = ""
    exploration: str = ""
    social: str = ""
    downtime: str = ""


class ExtractedRule(BaseModel):
    name: str
    content: str
    tags: List[str]


class RuleListExtraction(BaseModel):
    rules: List[ExtractedRule]


# ---------------------------------------------------------------------------
# WORLD GENERATION SCHEMAS (LEGACY BUT STILL USED)
#   - Used by WorldGenService and SetupWizard
# ---------------------------------------------------------------------------


class NpcData(BaseModel):
    name: str = Field(..., description="Name of the NPC.")
    visual_description: str = Field(..., description="Physical appearance.")
    stat_template: str = Field(
        ...,
        description="Archetype or template for stats (e.g. 'Guard', 'Civilian', 'Boss').",
    )
    initial_disposition: Literal["hostile", "neutral", "friendly"] = "neutral"


class LocationData(BaseModel):
    key: str = Field(..., description="Unique snake_case ID (e.g. 'loc_market').")
    name: str = Field(..., description="Display name (e.g. 'The Market').")
    description_visual: str = Field(
        ..., description="What the location looks like at a glance."
    )
    description_sensory: str = Field(
        ..., description="Other sensory details (sounds, smells, atmosphere)."
    )
    type: str = Field(
        ..., description="Category like indoor, outdoor, structure, district, etc."
    )
    # Optional: neighbors can be added at world-gen time by other logic, so we
    # keep this minimal here.


class LoreData(BaseModel):
    content: str
    tags: List[str]
    priority: int = 3
    kind: str = "lore"


class WorldExtraction(BaseModel):
    """
    Structure for extracting world details from raw text.
    Used by WorldGenService to build starting locations, NPCs, and lore.
    """

    genre: str = Field(
        ...,
        description="The specific sub-genre inferred from the text (e.g. 'Gothic Horror', 'Sword & Sorcery').",
    )
    tone: str = Field(
        ..., description="The atmospheric tone (e.g. 'grim', 'whimsical', 'noir')."
    )

    starting_location: LocationData = Field(
        ..., description="The initial scene location where play begins."
    )
    adjacent_locations: List[LocationData] = Field(
        default_factory=list,
        description="2–3 locations directly connected to the starting location.",
    )

    lore: List[LoreData] = Field(
        ...,
        description="Key facts, secrets, or world details that might become memories.",
    )

    initial_npcs: List[NpcData] = Field(
        default_factory=list,
        description="NPCs present in or immediately around the starting scene.",
    )
