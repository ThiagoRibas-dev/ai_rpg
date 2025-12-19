import logging
from typing import Any, Dict, List, Type

from pydantic import BaseModel, Field, create_model, ConfigDict

from app.prefabs.manifest import SystemManifest, FieldDef

logger = logging.getLogger(__name__)

# =============================================================================
# SUB-MODELS (Reusable building blocks)
# =============================================================================


class InventoryItem(BaseModel):
    name: str = ""
    qty: int = 1
    model_config = ConfigDict(extra="allow")


# =============================================================================
# SCHEMA BUILDER
# =============================================================================


class SchemaBuilder:
    """
    Constructs Pydantic models dynamically based on a SystemManifest.
    Used to constrain LLM outputs during character generation.
    """

    def __init__(self, manifest: SystemManifest):
        self.manifest = manifest
        self._cache: Dict[str, Type[BaseModel]] = {}

    def build_creation_prompt_model(self) -> Type[BaseModel]:
        """
        Builds a simplified Pydantic model for the LLM to fill out.

        Complex prefabs are flattened to simple types:
        - RES_POOL -> int (Represents the starting value/max)
        - RES_TRACK -> int (Represents filled boxes, usually 0)
        - CONT_LIST -> List[str] (Just names)
        """
        cache_key = "creation_prompt"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Group fields by category
        fields_by_cat: Dict[str, List[FieldDef]] = {}
        for field_def in self.manifest.fields:
            if field_def.category not in fields_by_cat:
                fields_by_cat[field_def.category] = []
            fields_by_cat[field_def.category].append(field_def)

        # Build sub-models for each category
        category_models: Dict[str, Any] = {}

        # Ensure identity exists even if not in fields
        if "identity" not in fields_by_cat:
            fields_by_cat["identity"] = []

        # Add Identity manually if missing fields (it usually is handled separately, but good to ensure)
        identity_fields = {
            "name": (str, Field(..., description="Character Name")),
            "description": (str, Field(..., description="Visual Description")),
            "concept": (
                str,
                Field(..., description="High Concept / Class / Archetype"),
            ),
        }
        IdentityModel = create_model("IdentityCreation", **identity_fields)
        category_models["identity"] = (
            IdentityModel,
            Field(default_factory=IdentityModel),
        )

        # Process other categories
        for cat, fields in fields_by_cat.items():
            if cat == "identity":
                continue  # Handled above

            model_fields = {}
            for f in fields:
                py_type, default = self._get_simplified_type_and_default(f)
                desc = f.label
                if f.usage_hint:
                    desc += f" ({f.usage_hint})"

                model_fields[f.path.split(".")[-1]] = (
                    py_type,
                    Field(default, description=desc)
                    if default is not None
                    else Field(..., description=desc),
                )

            if model_fields:
                CatModel = create_model(f"{cat.title()}Creation", **model_fields)
                category_models[cat] = (CatModel, Field(default_factory=CatModel))

        # Root Model
        CreationModel = create_model(
            "CharacterCreation", __config__=ConfigDict(extra="allow"), **category_models
        )

        self._cache[cache_key] = CreationModel
        return CreationModel

    def convert_simplified_to_full(
        self, simplified_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Expands the simplified LLM output (int/str) into full Prefab structures.
        e.g., {"hp": 10} -> {"hp": {"current": 10, "max": 10}}
        """
        result: Dict[str, Any] = {}

        for cat_key, cat_data in simplified_data.items():
            if not isinstance(cat_data, dict):
                result[cat_key] = cat_data
                continue

            result[cat_key] = {}

            # Find fields for this category
            cat_fields = {
                f.path.split(".")[-1]: f
                for f in self.manifest.get_fields_by_category(cat_key)
            }

            for field_key, value in cat_data.items():
                field_def = cat_fields.get(field_key)

                if field_def:
                    # Expand based on Prefab
                    result[cat_key][field_key] = self._expand_value(
                        field_def.prefab, value
                    )
                else:
                    # Pass through unknown fields (identity, etc)
                    result[cat_key][field_key] = value

        return result

    def _get_simplified_type_and_default(self, field_def: FieldDef) -> tuple[Type, Any]:
        """Map Prefab -> (PythonType, DefaultValue) for LLM prompting."""
        p = field_def.prefab

        # VAL Family
        if p == "VAL_INT":
            return (int, field_def.config.get("default", 0))
        if p == "VAL_COMPOUND":
            return (int, field_def.config.get("default", 10))  # Ask for Score
        if p == "VAL_STEP_DIE":
            return (str, field_def.config.get("default", "d6"))
        if p == "VAL_LADDER":
            return (int, field_def.config.get("default", 0))
        if p == "VAL_BOOL":
            return (bool, field_def.config.get("default", False))
        if p == "VAL_TEXT":
            return (str, field_def.config.get("default", ""))

        # RES Family
        if p == "RES_POOL":
            return (int, field_def.config.get("default_max", 10))  # Ask for Max
        if p == "RES_COUNTER":
            return (int, field_def.config.get("default", 0))
        if p == "RES_TRACK":
            return (int, 0)  # Ask for filled boxes (default 0)

        # CONT Family
        if p in ["CONT_LIST", "CONT_TAGS"]:
            return (List[str], [])
        if p == "CONT_WEIGHTED":
            return (List[str], [])

        return (Any, None)

    def _expand_value(self, prefab: str, value: Any) -> Any:
        """Hydrate simplified value into full structure."""
        if value is None:
            return None

        # RES_POOL: int -> {current, max}
        if prefab == "RES_POOL":
            try:
                val = int(value)
                return {"current": val, "max": val}
            except Exception as e:
                logger.warning(f"Failed to expand RES_POOL value '{value}': {e}")
                return {"current": 10, "max": 10}

        # VAL_COMPOUND: int -> {score: int, mod: 0} (Mod calc happens in validation pipeline)
        if prefab == "VAL_COMPOUND":
            try:
                return {"score": int(value), "mod": 0}
            except Exception as e:
                logger.warning(f"Failed to expand VAL_COMPOUND value '{value}': {e}")
                return {"score": 10, "mod": 0}

        # VAL_LADDER: int -> {value: int, label: ""}
        if prefab == "VAL_LADDER":
            try:
                return {"value": int(value), "label": ""}
            except Exception as e:
                logger.warning(f"Failed to expand VAL_LADDER value '{value}': {e}")
                return {"value": 0, "label": ""}
        
        # VAL_TEXT
        if prefab == "VAL_TEXT":
            return str(value) if value else ""

        # CONT_LIST / WEIGHTED: List[str] -> List[{name: str, ...}]
        if prefab in ["CONT_LIST", "CONT_WEIGHTED"]:
            if isinstance(value, list):
                return [
                    {"name": str(x), "qty": 1} if isinstance(x, str) else x
                    for x in value
                ]

        return value

    def get_creation_prompt_hints(self) -> str:
        """Returns text explaining the fields to the AI."""
        return self.manifest.get_path_hints()
