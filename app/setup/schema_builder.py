from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field, create_model

from app.models.vocabulary import CategoryName, ConfigKey, FieldKey, PrefabID
from app.prefabs.manifest import FieldDef, SystemManifest

logger = logging.getLogger(__name__)

# =============================================================================
# SUB-MODELS (Reusable building blocks)
# =============================================================================


class InventoryItem(BaseModel):
    name: str = Field("", description="Item name.")
    qty: int = Field(1, description="Quantity of this item.")
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
        self._cache: dict[str, type[BaseModel]] = {}

    def build_creation_prompt_model(self) -> type[BaseModel]:
        """
        Builds a strict Pydantic model for the LLM to fill out, derived from the SystemManifest.

        Rules:
        - Complex prefabs are flattened to simple primitives:
          - RES_POOL -> int (represents Max; current is set to Max on creation)
          - RES_TRACK -> int (number of filled boxes)
          - CONT_LIST / CONT_TAGS / CONT_WEIGHTED -> List[str] (item names)
        - Derived fields (formula / max_formula) are NOT included; validate_entity computes them.
        - extra="forbid" at all levels to disallow unknown keys.
        """
        cache_key = "creation_prompt"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # 1. Group non-derived fields by category
        fields_by_cat: dict[str, list[FieldDef]] = {}
        for field_def in self.manifest.fields:
            # Skip purely derived stats; formulas and max_formulas are handled by validate_entity
            if field_def.formula or field_def.max_formula:
                continue
            fields_by_cat.setdefault(field_def.category, []).append(field_def)

        # Ensure identity exists even if not defined explicitly in manifest
        if CategoryName.IDENTITY not in fields_by_cat:
            fields_by_cat[CategoryName.IDENTITY] = []

        # 2. Build strict sub-models per category
        category_models: dict[str, Any] = {}

        for cat, fields in fields_by_cat.items():
            model_fields: dict[str, Any] = {}

            for field in fields:
                py_type, default = self._get_simplified_type_and_default(field)
                desc = field.label
                if field.usage_hint:
                    desc += f" ({field.usage_hint})"

                field_name = field.path.split(".")[-1]

                if default is not None:
                    model_fields[field_name] = (
                        py_type,
                        Field(default, description=desc),
                    )
                else:
                    model_fields[field_name] = (
                        py_type,
                        Field(..., description=desc),
                    )

            # Identity: ensure core text fields even if manifest doesn't define them
            if cat == CategoryName.IDENTITY:
                if "name" not in model_fields:
                    model_fields["name"] = (
                        str,
                        Field(..., description="Character Name"),
                    )
                if "description" not in model_fields:
                    model_fields["description"] = (
                        str,
                        Field("", description="Visual / narrative description"),
                    )
                if "concept" not in model_fields:
                    model_fields["concept"] = (
                        str,
                        Field("", description="High Concept / Elevator Pitch"),
                    )

            if not model_fields:
                continue

            # 2.1 Category Model: not strict internally to allow future expansion
            cat_model = create_model(
                f"{cat.title()}Creation",
                __config__=ConfigDict(),
                **cast(dict[str, Any], model_fields),
            )
            category_models[cat] = (
                cat_model,
                Field(..., description=f"{cat.title()} category"),
            )


        # 3. Root Model: strict, no extra top-level categories
        creation_model = create_model(
            "CharacterCreation",
            __config__=ConfigDict(extra="forbid"),
            **cast(dict[str, Any], category_models),
        )


        typed_model = cast(type[BaseModel], creation_model)
        self._cache[cache_key] = typed_model
        return typed_model

    def build_creation_model_for_category(self, category: str) -> type[BaseModel]:
        """Builds a strict Pydantic model for a single category."""
        cache_key = f"creation_prompt_cat_{category}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        fields = [f for f in self.manifest.fields if f.category == category]
        model_fields: dict[str, Any] = {}

        for field in fields:
            if field.formula or field.max_formula:
                continue

            py_type, default = self._get_simplified_type_and_default(field)
            desc = field.label
            if field.usage_hint:
                desc += f" ({field.usage_hint})"

            field_name = field.path.split(".")[-1]

            if default is not None:
                model_fields[field_name] = (py_type, Field(default, description=desc))
            else:
                model_fields[field_name] = (py_type, Field(..., description=desc))

        if category == CategoryName.IDENTITY:
            if "name" not in model_fields:
                model_fields["name"] = (str, Field(..., description="Character Name"))
            if "description" not in model_fields:
                model_fields["description"] = (str, Field("", description="Visual / narrative description"))
            if "concept" not in model_fields:
                model_fields["concept"] = (str, Field("", description="High Concept / Elevator Pitch"))

        if not model_fields:
            cat_model = create_model(f"{category.title()}Creation", __config__=ConfigDict(extra="forbid"))
            self._cache[cache_key] = cat_model
            return cat_model

        cat_model = create_model(
            f"{category.title()}Creation",
            __config__=ConfigDict(extra="forbid"),
            **cast(dict[str, Any], model_fields),
        )


        typed_model = cast(type[BaseModel], cat_model)
        self._cache[cache_key] = typed_model
        return typed_model

    def build_prefab_schema_reference(self) -> str:
        """Builds a markdown reference for all Prefab data shapes to guide the LLM."""
        from app.prefabs.registry import PREFABS

        lines = ["## PREFAB STRUCTURES", "Use these exact data shapes when the schema indicates a prefab type."]
        for family, family_name in [("VAL", "Values"), ("RES", "Resources"), ("CONT", "Containers")]:
            lines.append(f"\n### {family_name}")
            for prefab in PREFABS.values():
                if prefab.family == family:
                    import json
                    shape_str = json.dumps(prefab.shape) if isinstance(prefab.shape, dict | list) else str(prefab.shape)
                    lines.append(f"- **{prefab.id}**: {shape_str}  *(Hint: {prefab.ai_hint})*")

        return "\n".join(lines)

    def convert_simplified_to_full(
        self, simplified_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Expands the simplified LLM output (int/str) into full Prefab structures.
        e.g., {"hp": 10} -> {"hp": {"current": 10, "max": 10}}
        """
        result: dict[str, Any] = {}

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

    def _get_simplified_type_and_default(self, field_def: FieldDef) -> tuple[type, Any]:
        """Map Prefab -> (PythonType, DefaultValue) for LLM prompting."""
        p = field_def.prefab

        # VALUE FIELDS
        if p == PrefabID.VAL_INT:
            return int, field_def.config.get(ConfigKey.DEFAULT, 0)
        if p == PrefabID.VAL_COMPOUND:
            # Ask the LLM for the score; modifier will be derived by validate_entity
            return int, field_def.config.get(ConfigKey.DEFAULT, 10)
        if p == PrefabID.VAL_LADDER:
            return int, field_def.config.get(ConfigKey.DEFAULT, 0)
        if p == PrefabID.VAL_BOOL:
            return bool, field_def.config.get(ConfigKey.DEFAULT, False)
        if p == PrefabID.VAL_TEXT:
            return str, field_def.config.get(ConfigKey.DEFAULT, "")

        # RESOURCES
        if p == PrefabID.RES_POOL:
            # Ask for Max only; current will start at Max on creation
            return int, field_def.config.get(ConfigKey.DEFAULT_MAX, 10)
        if p == PrefabID.RES_COUNTER:
            return int, field_def.config.get(ConfigKey.DEFAULT, 0)
        if p == PrefabID.RES_TRACK:
            # Number of filled boxes
            return int, 0

        # CONTAINERS
        if p in [PrefabID.CONT_LIST, PrefabID.CONT_WEIGHTED, PrefabID.CONT_TAGS]:
            # SPECIAL CASE: structured list items (e.g. spell_slots)
            item_shape = field_def.config.get(ConfigKey.ITEM_SHAPE)
            if p == PrefabID.CONT_LIST and item_shape:
                item_model = self._build_item_model(field_def)
                return list[item_model], []  # type: ignore[valid-type]


            # Default behaviour: list of simple names/tags
            return list[str], []

        # Fallback: treat as free-form text
        return str, ""

    def _expand_value(self, prefab: str, value: Any) -> Any:
        """Hydrate simplified value into full structure."""
        if value is None:
            return None

        # RES_POOL: int -> {current, max}
        if prefab == PrefabID.RES_POOL:
            try:
                val = int(value)
                return {FieldKey.CURRENT: val, FieldKey.MAX: val}
            except Exception as e:
                logger.warning(f"Failed to expand RES_POOL value '{value}': {e}")
                return {FieldKey.CURRENT: 10, FieldKey.MAX: 10}

        # VAL_COMPOUND: int -> {score: int, mod: 0} (Mod calc happens in validation pipeline)
        if prefab == PrefabID.VAL_COMPOUND:
            try:
                return {FieldKey.SCORE: int(value), FieldKey.MOD: 0}
            except Exception as e:
                logger.warning(f"Failed to expand VAL_COMPOUND value '{value}': {e}")
                return {FieldKey.SCORE: 10, FieldKey.MOD: 0}

        # VAL_LADDER: int -> {value: int, label: ""}
        if prefab == PrefabID.VAL_LADDER:
            try:
                return {FieldKey.VALUE: int(value), FieldKey.LABEL: ""}
            except Exception as e:
                logger.warning(f"Failed to expand VAL_LADDER value '{value}': {e}")
                return {FieldKey.VALUE: 0, FieldKey.LABEL: ""}

        # VAL_TEXT
        if prefab == PrefabID.VAL_TEXT:
            return str(value) if value else ""

        # CONT_LIST / WEIGHTED: List[str] -> List[{name: str, ...}]
        if prefab in [PrefabID.CONT_LIST, PrefabID.CONT_WEIGHTED]:
            if isinstance(value, list):
                return [
                    {FieldKey.NAME: str(x), FieldKey.QTY: 1} if isinstance(x, str) else x
                    for x in value
                ]

        return value

    def get_creation_prompt_hints(self, categories: Sequence[str] | None = None) -> str:
        """Returns text explaining the fields to the AI, optionally filtered by category."""
        return self.get_filtered_path_hints(categories) if categories else self.manifest.get_path_hints()

    def get_filtered_path_hints(self, categories: Sequence[str]) -> str:
        """Returns hint text ONLY for the requested categories."""
        lines = ["## VALID PATHS FOR THIS BATCH"]
        from app.prefabs.registry import PREFABS

        for category in categories:
            fields = self.manifest.get_fields_by_category(category)
            if not fields:
                continue
            lines.append(f"\n**{category.title()}:**")
            for f in fields:
                # Skip derived fields as they aren't generated by the LLM
                if f.formula or f.max_formula:
                    continue

                prefab = PREFABS.get(f.prefab)
                hint = prefab.ai_hint if prefab else ""
                suffix = ".current" if f.prefab == PrefabID.RES_POOL else ""

                # Include item_shape info for complex containers
                usage = f.usage_hint
                if not usage and f.config.get(ConfigKey.ITEM_SHAPE):
                    shape = f.config[ConfigKey.ITEM_SHAPE]
                    usage = f"List of items with shape: {shape}"

                hint_text = f"  - `{f.path}{suffix}`: {f.label}"
                if hint:
                    hint_text += f" ({hint})"
                if usage:
                    hint_text += f" | Hint: {usage}"

                lines.append(hint_text)
        return "\n".join(lines)

    def _build_item_model(self, field_def: FieldDef) -> type[BaseModel]:
        """
        Build (and cache) a Pydantic model for a CONT_LIST item when
        field_def.config['item_shape'] is present.
        Example shape:
            {"class_name": "str", "spell_level": "int", "slots_max": "int", "slots_current": "int"}
        """
        cache_key = f"item_model:{field_def.path}"
        if cache_key in self._cache:
            return self._cache[cache_key]  # type: ignore[return-value]

        item_shape: dict[str, str] = field_def.config.get(ConfigKey.ITEM_SHAPE, {})
        model_fields: dict[str, Any] = {}

        for name, type_name in item_shape.items():
            if type_name == "int":
                py_type: type = int
                default: Any = 0
            else:
                # default to string for unknowns
                py_type = str
                default = ""

            desc = f"{field_def.label} - {name.replace('_', ' ').title()}"
            model_fields[name] = (py_type, Field(default, description=desc))

        item_model = create_model(
            f"{field_def.path.replace('.', '_').title()}Item",
            __config__=ConfigDict(extra="forbid"),
            **cast(dict[str, Any], model_fields),
        )

        typed_model = cast(type[BaseModel], item_model)
        self._cache[cache_key] = typed_model
        return typed_model
