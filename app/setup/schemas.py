from typing import Literal, Dict, Any, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
import re

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
    dice_notation: str = Field(
        ...,
        description="Primary dice expression used by the system (e.g. '1d20', '2d6').",
    )
    resolution_mechanic: str = Field(
        ...,
        description="How actions are resolved (e.g. 'Roll + Stat vs DC').",
    )
    success_condition: str = Field(
        ...,
        description="What counts as success (e.g. 'Result >= Target').",
    )
    crit_rules: str = Field(
        ...,
        description="How critical successes and failures work.",
    )
    fumble_rules: str = Field(
        "",
        description="Rules for fumbles or critical failures, if any.",
    )
    aliases: Dict[str, str] = Field(
        default_factory=dict,
        description="Global derived stats and formulas (e.g. 'str_mod').",
    )


class ProceduresExtraction(BaseModel):
    combat: str = Field(
        "",
        description="Step-by-step procedure text for resolving combat.",
    )
    exploration: str = Field(
        "",
        description="Procedure text for exploration scenes (movement, checks, rest).",
    )
    social: str = Field(
        "",
        description="Procedure text for social interactions and influence scenes.",
    )
    downtime: str = Field(
        "",
        description="Procedure text for downtime (healing, training, projects, etc.).",
    )
    character_creation: str = Field(
        "",
        description="Step-by-step procedure text for building a new character.",
    )


class ExtractedRule(BaseModel):
    name: str = Field(
        ...,
        description="Short name for the rule or mechanic (e.g. 'Falling Damage').",
    )
    content: str = Field(
        ...,
        description="Human-readable summary of the rule or mechanic.",
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Category tags (e.g. ['combat', 'movement']).",
    )


class RuleListExtraction(BaseModel):
    rules: List[ExtractedRule] = Field(
        default_factory=list,
        description="List of extracted rules/mechanics.",
    )


# ---------------------------------------------------------------------------
# WORLD GENERATION SCHEMAS (used by WorldGenService & SetupWizard)
# ---------------------------------------------------------------------------


class NpcData(BaseModel):
    name: str = Field(..., description="Name of the NPC.")
    visual_description: str = Field(
        ..., description="Physical / narrative description."
    )
    stat_template: str = Field(
        "default",
        description="Archetype (e.g. 'Guard', 'Civilian', 'Boss'). If unknown, use 'default'.",
    )
    initial_disposition: Literal["hostile", "neutral", "friendly"] = Field(
        "neutral",
        description="The NPC's initial attitude toward the player accounting for eprsonal history (or lack thereof), faction affiliation, place of origin, and other such factors.",
    )

    @model_validator(mode="before")
    @classmethod
    def normalize(cls, data: Any):
        """
        Accept shapes like:
        {
          "name": "Very Young Gold Dragon",
          "role": "...",
          "traits": ["...", "..."],
          "affiliation": "..."
        }
        and map them into the NpcData fields.
        """
        if not isinstance(data, dict):
            return data

        # Build a descriptive text from role + traits if visual_description missing
        if "visual_description" not in data:
            parts: List[str] = []
            role = data.get("role")
            if isinstance(role, str) and role.strip():
                parts.append(role.strip())
            traits = data.get("traits")
            if isinstance(traits, list) and traits:
                parts.append("Traits: " + ", ".join(str(t) for t in traits))
            aff = data.get("affiliation")
            if isinstance(aff, str) and aff.strip():
                parts.append(f"Affiliation: {aff.strip()}")
            if parts:
                data["visual_description"] = " ".join(parts)

        # Default stat_template if missing
        data.setdefault("stat_template", "default")

        return data


class LocationData(BaseModel):
    key: str = Field(
        ...,
        description="Unique snake_case ID (e.g. 'loc_market'). Will be auto-generated from name if omitted.",
    )
    name: str = Field(
        ...,
        description="Display name (e.g. 'The Market').",
    )
    description_visual: str = Field(
        ...,
        description="What the location looks like at a glance.",
    )
    description_sensory: str = Field(
        ...,
        description="Other sensory details (sounds, smells, atmosphere).",
    )
    type: str = Field(
        ...,
        description="indoor, outdoor, structure, district, etc.",
    )

    @model_validator(mode="before")
    @classmethod
    def normalize(cls, data: Any):
        """
        Make LocationData tolerant of simpler outputs like:
        {
          "name": "Shrine of the Holy Order of the Moons",
          "type": "shrine",
          "description": "Modest stone altar..."
        }
        or even:
        {
          "description": "A narrow trade road..."
        }
        """
        if not isinstance(data, dict):
            return data

        # Map single 'description' field into both visual & sensory if specific ones missing
        desc = data.get("description")
        if isinstance(desc, str) and desc.strip():
            data.setdefault("description_visual", desc)
            data.setdefault("description_sensory", desc)

        # Ensure we have a name
        if not data.get("name"):
            # Try 'title' if provided
            if isinstance(data.get("title"), str) and data["title"].strip():
                data["name"] = data["title"].strip()
            else:
                data["name"] = "Starting Location"

        # Generate a key if missing or empty
        if not data.get("key"):
            base = data.get("name", "loc_start")
            slug = re.sub(r"[^a-z0-9_]+", "", base.lower().replace(" ", "_"))
            data["key"] = slug or "loc_start"

        # Default type if omitted
        data.setdefault("type", "unspecified")

        return data


class LoreData(BaseModel):
    content: str = Field(
        ...,
        description="The content/fact/detail about the world.",
    )
    tags: List[str] = Field(
        ...,
        description="Categories or keywords associated with this lore item.",
    )
    priority: int = 3
    kind: str = "lore"

    @model_validator(mode="before")
    @classmethod
    def normalize(cls, data: Any):
        """
        Accepts:
        - Full LoreData shape: {"content": "...", "tags": [...], ...}
        - The JSON your backend returns: {"category": "...", "details": "..."}
        - Or even plain strings: "Some fact about the world"
        """
        # Already in nice shape
        if isinstance(data, dict) and "content" in data:
            # Ensure tags list exists
            data.setdefault("tags", [])
            data.setdefault("priority", 3)
            data.setdefault("kind", "lore")
            return data

        # Backend shape: {"category": "...", "details": "..."}
        if isinstance(data, dict) and "details" in data:
            category = str(data.get("category") or "world_gen")
            details = str(data["details"])
            return {
                "content": details,
                "tags": [category, "world_gen"],
                "priority": 3,
                "kind": "lore",
            }

        # Plain string fallback
        if isinstance(data, str):
            return {
                "content": data,
                "tags": ["world_gen"],
                "priority": 3,
                "kind": "lore",
            }

        return data


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
        default_factory=list,
        description="Key facts, secrets, or world details that might become memories.",
    )
    initial_npcs: List[NpcData] = Field(
        default_factory=list,
        description="NPCs present in or immediately around the starting scene.",
    )

    @model_validator(mode="before")
    @classmethod
    def normalize(cls, data: Any):
        """
        Glue layer between the loose JSON shape from the model and our stricter schema.

        Handles:
        - starting_location.adjacent_locations -> top-level adjacent_locations (if needed)
        - starting_location.lore -> top-level lore (if top-level missing)
        - starting_location.npcs / 'npcs' -> initial_npcs
        """
        if not isinstance(data, dict):
            return data

        # If the model nested things under starting_location, lift them up if top-level missing
        sl = data.get("starting_location")
        if isinstance(sl, dict):
            # Move nested adjacent_locations up if not already present
            if "adjacent_locations" not in data and "adjacent_locations" in sl:
                data["adjacent_locations"] = sl["adjacent_locations"]

            # Move nested lore up if not already present
            if "lore" not in data and "lore" in sl:
                data["lore"] = sl["lore"]

            # Nested npcs -> initial_npcs if missing
            if "initial_npcs" not in data and "npcs" in sl:
                data["initial_npcs"] = sl["npcs"]

        # Some models might use alternate names
        if "startingLocation" in data and "starting_location" not in data:
            data["starting_location"] = data["startingLocation"]
        if "adjacent" in data and "adjacent_locations" not in data:
            data["adjacent_locations"] = data["adjacent"]
        if "npcs" in data and "initial_npcs" not in data:
            data["initial_npcs"] = data["npcs"]

        # Ensure lists exist
        data.setdefault("adjacent_locations", [])
        data.setdefault("lore", [])
        data.setdefault("initial_npcs", [])

        return data
