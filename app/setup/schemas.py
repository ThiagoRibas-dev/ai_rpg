import asyncio
import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.vocabulary import CategoryName, MemoryKind, PrefabID, WorldCategory, WORLD_GEN_TAG

# ---------------------------------------------------------------------------
# PREFAB / MANIFEST EXTRACTION SCHEMAS
# ---------------------------------------------------------------------------

class ExtractedField(BaseModel):
    label: str
    path: str = Field(..., description="snake_case.path")
    prefab: PrefabID
    category: CategoryName
    config: dict[str, Any] = Field(default_factory=dict)
    formula: str | None = None
    usage_hint: str = Field(..., description="Short explanation for the AI")

    @field_validator("prefab", mode="before")
    @classmethod
    def sanitize(cls, v):
        # Map some looser LLM outputs to real prefab IDs
        mapping = {
            "VAL_NUMBER": PrefabID.VAL_INT,
            "RES_BAR": PrefabID.RES_POOL,
            "VAL_DIE": PrefabID.VAL_STEP_DIE,
            "CONT_ARRAY": PrefabID.CONT_LIST,
        }
        return mapping.get(v, v)


class ExtractedFieldList(BaseModel):
    fields: list[ExtractedField]


class MechanicsExtraction(BaseModel):
    system_name: str = Field(
        "",
        description="Official or common published name of the RPG system.",
    )
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
    aliases: dict[str, str] = Field(
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
    tags: list[str] = Field(
        default_factory=list,
        description="Category tags (e.g. ['combat', 'movement']).",
    )


class RuleListExtraction(BaseModel):
    rules: list[ExtractedRule] = Field(
        default_factory=list,
        description="List of extracted rules/mechanics.",
    )


# ---------------------------------------------------------------------------
# WORLD GENERATION SCHEMAS (used by WorldGenService & SetupWizard)
# ---------------------------------------------------------------------------


class NpcData(BaseModel):
    model_config = {"extra": "forbid"}
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
    tags: list[str] = Field(
        default_factory=list, description="Tags associated with this NPC."
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
            parts: list[str] = []
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
    model_config = {"extra": "forbid"}
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
    tags: list[str] = Field(
        default_factory=list, description="Tags associated with this location."
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

        # Map synonyms and shortcuts
        if not isinstance(data, dict):
             return data

        # Specific llama.cpp hallucinations
        if "meta" in data and not data.get("description_visual"):
            data["description_visual"] = data.pop("meta")
        if "sensory" in data and not data.get("description_sensory"):
            data["description_sensory"] = data.pop("sensory")
        if "threats" in data and not data.get("starting_threats"):
            data["starting_threats"] = data.pop("threats")
        elif "threat" in data and not data.get("starting_threats"):
            data["starting_threats"] = data.pop("threat")

        # Map single 'description' field into both visual & sensory if specific ones missing
        desc = data.get("description")
        if isinstance(desc, str) and desc.strip():
            if not data.get("description_visual"):
                data["description_visual"] = desc
            if not data.get("description_sensory"):
                data["description_sensory"] = desc

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
    model_config = {"extra": "forbid"}
    name: str = Field(
        ...,
        description="The name of the lore entity or topic.",
    )
    content: str = Field(
        ...,
        description="The content/fact/detail about the world.",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Categories or keywords associated with this lore item.",
    )
    priority: int = 3
    kind: str = MemoryKind.LORE

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
            data.setdefault("kind", MemoryKind.LORE)

            # Ensure name exists
            if "name" not in data:
                # Use first tag if available, or first 20 chars of content
                if data["tags"]:
                    data["name"] = str(data["tags"][0]).title()
                else:
                    data["name"] = data["content"][:20] + "..."

            return data

        # Backend shape: {"category": "...", "details": "..."}
        if isinstance(data, dict) and "details" in data:
            category = str(data.get("category") or WORLD_GEN_TAG)
            details = str(data["details"])
            return {
                "name": category.title(),
                "content": details,
                "tags": [category, WORLD_GEN_TAG],
                "priority": 3,
                "kind": MemoryKind.LORE,
            }

        # Plain string fallback
        if isinstance(data, str):
            return {
                "content": data,
                "tags": [WORLD_GEN_TAG],
                "priority": 3,
                "kind": MemoryKind.LORE,
            }

        return data



# --- WRAPPERS FOR MULTI-STAGE WORLD GEN ---

class GenreToneExtraction(BaseModel):
    genre: str = Field(
        ...,
        description="The specific sub-genre inferred from the text (e.g. 'Gothic Horror', 'Sword & Sorcery').",
    )
    tone: str = Field(
        ..., description="The atmospheric tone (e.g. 'grim', 'whimsical', 'noir')."
    )

class LoreListExtraction(BaseModel):
    lore: list[LoreData] = Field(
        default_factory=list,
        description="Key facts, secrets, world details, lore, etc.",
    )

class WorldIndexItem(BaseModel):
    name: str = Field(..., description="The unique name of the entity.")
    type: WorldCategory = Field(..., description="The entity type (including lore sub-categories).")

class WorldIndexExtraction(BaseModel):
    items: list[WorldIndexItem] = Field(default_factory=list)

class LocationListExtraction(BaseModel):
    locations: list[LocationData] = Field(
        default_factory=list,
        description="Locations directly mentioned or implied and their connections to one another.",
    )

class NpcListExtraction(BaseModel):
    npcs: list[NpcData] = Field(
        default_factory=list,
        description="All NPCs (characters, creatures, entities, etc.) mentioned or implied in the text.",
    )

class WorldEntitiesExtraction(BaseModel):
    locations: list[LocationData] = Field(
        default_factory=list,
        description="Locations directly mentioned or implied and their connections to one another.",
    )
    npcs: list[NpcData] = Field(
        default_factory=list,
        description="All NPCs (characters, creatures, entities, etc.) mentioned or implied in the text.",
    )

class WorldExtraction(BaseModel):
    model_config = {"extra": "forbid"}
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
    adjacent_locations: list[LocationData] = Field(
        default_factory=list,
        description="Locations directly connected to the starting location.",
    )
    lore: list[LoreData] = Field(
        default_factory=list,
        description="Key facts, secrets, or world details that might become memories.",
    )
    initial_npcs: list[NpcData] = Field(
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


class LoreStream:
    """
    Asynchronous coordination object for sharing world data with character generation.
    """

    def __init__(self):
        self._npc_future: asyncio.Future[list[NpcData]] | None = None

    def _ensure_future(self) -> asyncio.Future[list[NpcData]]:
        if self._npc_future is None:
            self._npc_future = asyncio.get_event_loop().create_future()
        return self._npc_future

    def set_npcs(self, npcs: list[NpcData]):
        """Fulfills the promise of NPC data."""
        fut = self._ensure_future()
        if not fut.done():
            fut.set_result(npcs)

    def set_error(self, exc: Exception):
        """Propagates failure to any waiting consumers."""
        fut = self._ensure_future()
        if not fut.done():
            fut.set_exception(exc)

    async def get_npcs(self) -> list[NpcData]:
        """Blocks until NPCs are available and returns them."""
        fut = self._ensure_future()
        return await fut
