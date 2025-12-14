"""
Schema Builder
==============
Dynamically generates Pydantic models AND UI Specs from a GameVocabulary.
"""

import logging
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel, Field, create_model, ConfigDict

from app.models.vocabulary import (
    GameVocabulary,
    FieldDefinition,
    FieldType,
    SemanticRole,
)
from app.models.sheet_schema import CharacterSheetSpec, SheetField, FieldDisplay

logger = logging.getLogger(__name__)

# =============================================================================
# SUB-MODELS (Reusable building blocks)
# =============================================================================


class PoolValue(BaseModel):
    current: int = 0
    max: int = 10
    model_config = ConfigDict(extra="allow")


class LadderValue(BaseModel):
    value: int = 0
    label: str = ""
    model_config = ConfigDict(extra="allow")


class TagValue(BaseModel):
    text: str = ""
    free_invokes: int = 0
    model_config = ConfigDict(extra="allow")


class InventoryItem(BaseModel):
    name: str = ""
    description: str = ""
    quantity: int = 1
    model_config = ConfigDict(extra="allow")


# =============================================================================
# SCHEMA BUILDER
# =============================================================================


class SchemaBuilder:
    def __init__(self, vocabulary: GameVocabulary):
        self.vocab = vocabulary
        self._cache: Dict[str, Type[BaseModel]] = {}

    # -------------------------------------------------------------------------
    # UI SPEC BUILDER (Vocabulary -> CharacterSheetSpec)
    # -------------------------------------------------------------------------
    def build_sheet_spec(self) -> CharacterSheetSpec:
        """
        Converts the GameVocabulary into a UI Specification.
        This allows the CharacterInspector to render the sheet defined by the rules.
        """
        spec = CharacterSheetSpec()

        # Map SemanticRole to SheetCategory
        role_map = {
            SemanticRole.CORE_TRAIT: spec.attributes,
            SemanticRole.RESOURCE: spec.resources,
            SemanticRole.CAPABILITY: spec.skills,
            SemanticRole.STATUS: spec.features,
            SemanticRole.ASPECT: spec.narrative,
            SemanticRole.PROGRESSION: spec.progression,
            SemanticRole.EQUIPMENT: spec.inventory,
            SemanticRole.CONNECTION: spec.connections,
        }

        for role in SemanticRole:
            target_cat = role_map.get(role)
            if not target_cat:
                continue

            fields = self.vocab.get_fields_by_role(role)
            for key, field_def in fields.items():
                sheet_field = self._convert_def_to_sheet_field(field_def)
                target_cat.fields[key] = sheet_field

        return spec

    def _convert_def_to_sheet_field(self, f: FieldDefinition) -> SheetField:
        """Helper to convert a Vocabulary FieldDefinition to a UI SheetField."""

        container = "atom"
        dtype = "string"
        widget = "text"
        components = None
        item_schema = None

        if f.field_type == FieldType.NUMBER:
            dtype = "number"
            widget = "number"
        elif f.field_type == FieldType.TEXT:
            dtype = "string"
            widget = "text"
        elif f.field_type == FieldType.DIE:
            dtype = "string"
            widget = "die"
        elif f.field_type == FieldType.POOL:
            container = "molecule"
            widget = "pool"
            components = {
                "current": SheetField(
                    key="current",
                    container_type="atom",
                    data_type="number",
                    default=f.default_value or 10,
                    display=FieldDisplay(label="Cur", widget="number"),
                ),
                "max": SheetField(
                    key="max",
                    container_type="atom",
                    data_type="number",
                    default=f.default_value or 10,
                    display=FieldDisplay(label="Max", widget="number"),
                ),
            }
        elif f.field_type == FieldType.TRACK:
            container = "molecule"
            widget = "track"
            components = {
                "value": SheetField(
                    key="value",
                    container_type="atom",
                    data_type="number",
                    default=0,
                    display=FieldDisplay(label="Filled", widget="number"),
                )
            }
        elif f.field_type == FieldType.LADDER:
            container = "molecule"
            widget = "ladder"
            components = {
                "value": SheetField(
                    key="value",
                    container_type="atom",
                    data_type="number",
                    default=0,
                    display=FieldDisplay(label="Val"),
                ),
                "label": SheetField(
                    key="label",
                    container_type="atom",
                    data_type="string",
                    default="",
                    display=FieldDisplay(label="Label"),
                ),
            }
        elif f.field_type == FieldType.LIST:
            container = "list"
            widget = "repeater"
            item_schema = {
                "name": SheetField(key="name", display=FieldDisplay(label="Name")),
                "description": SheetField(
                    key="description", display=FieldDisplay(label="Desc")
                ),
            }

        return SheetField(
            key=f.key,
            container_type=container,
            data_type=dtype,
            default=f.default_value,
            components=components,
            item_schema=item_schema,
            display=FieldDisplay(label=f.label, widget=widget, options=None),
        )

    # -------------------------------------------------------------------------
    # PYDANTIC MODEL BUILDERS
    # -------------------------------------------------------------------------

    def build_character_model(self) -> Type[BaseModel]:
        cache_key = "character"
        if cache_key in self._cache:
            return self._cache[cache_key]

        role_models: Dict[str, Any] = {}
        for role in SemanticRole:
            role_fields = self.vocab.get_fields_by_role(role)
            if not role_fields:
                continue
            role_model = self._build_role_model(role, role_fields)
            role_models[role.value] = (role_model, Field(default_factory=role_model))

        if "identity" not in role_models:
            identity_model = self._build_identity_model()
            role_models["identity"] = (
                identity_model,
                Field(default_factory=identity_model),
            )

        CharacterModel = create_model(
            "Character", __config__=ConfigDict(extra="allow"), **role_models
        )
        self._cache[cache_key] = CharacterModel
        return CharacterModel

    def build_creation_prompt_model(self) -> Type[BaseModel]:
        cache_key = "creation_prompt"
        if cache_key in self._cache:
            return self._cache[cache_key]

        role_models: Dict[str, Any] = {}
        for role in SemanticRole:
            role_fields = self.vocab.get_fields_by_role(role)
            if not role_fields:
                continue
            simplified = self._build_simplified_role_model(role, role_fields)
            role_models[role.value] = (simplified, Field(default_factory=simplified))

        if "identity" not in role_models:
            identity = self._build_identity_model()
            role_models["identity"] = (identity, Field(default_factory=identity))

        CreationModel = create_model(
            "CharacterCreation", __config__=ConfigDict(extra="allow"), **role_models
        )
        self._cache[cache_key] = CreationModel
        return CreationModel

    def _build_role_model(
        self, role: SemanticRole, fields: Dict[str, FieldDefinition]
    ) -> Type[BaseModel]:
        model_fields: Dict[str, Any] = {}
        for key, field_def in fields.items():
            py_type = self._get_python_type(field_def)
            default = self._get_default_value(field_def)
            model_fields[key] = (
                (Optional[py_type], None)
                if default is None
                else (py_type, Field(default=default))
            )

        return create_model(
            f"{role.value.title().replace('_', '')}Fields",
            __config__=ConfigDict(extra="allow"),
            **model_fields,
        )

    def _build_simplified_role_model(
        self, role: SemanticRole, fields: Dict[str, FieldDefinition]
    ) -> Type[BaseModel]:
        model_fields: Dict[str, Any] = {}
        for key, field_def in fields.items():
            py_type, default = self._get_simplified_type_and_default(field_def)
            model_fields[key] = (
                (Optional[py_type], None)
                if default is None
                else (py_type, Field(default=default))
            )

        return create_model(
            f"{role.value.title().replace('_', '')}Creation",
            __config__=ConfigDict(extra="allow"),
            **model_fields,
        )

    def _build_identity_model(self) -> Type[BaseModel]:
        return create_model(
            "Identity",
            __config__=ConfigDict(extra="allow"),
            name=(str, Field(default="")),
            description=(str, Field(default="")),
            concept=(str, Field(default="")),
            player_name=(str, Field(default="")),
        )

    # -------------------------------------------------------------------------
    # TYPE RESOLUTION helpers
    # -------------------------------------------------------------------------
    def _get_python_type(self, field_def: FieldDefinition) -> Type:
        ft = field_def.field_type
        if ft == FieldType.NUMBER:
            return int
        elif ft == FieldType.POOL:
            return PoolValue
        elif ft == FieldType.TRACK:
            return List[bool]
        elif ft == FieldType.DIE:
            return str
        elif ft == FieldType.LADDER:
            return LadderValue
        elif ft == FieldType.TAG:
            return Union[str, TagValue]
        elif ft == FieldType.TEXT:
            return str
        elif ft == FieldType.LIST:
            return List[InventoryItem]
        return Any

    def _get_simplified_type_and_default(
        self, field_def: FieldDefinition
    ) -> tuple[Type, Any]:
        ft = field_def.field_type
        if ft == FieldType.NUMBER:
            return int, field_def.default_value or 0
        elif ft == FieldType.POOL:
            return int, field_def.default_value or 10  # ask for max
        elif ft == FieldType.TRACK:
            return int, 0  # ask for boxes filled
        elif ft == FieldType.DIE:
            return str, field_def.die_default or "d6"
        elif ft == FieldType.LADDER:
            return int, field_def.default_value or 0
        elif ft == FieldType.TAG:
            return str, ""
        elif ft == FieldType.TEXT:
            return str, ""
        elif ft == FieldType.LIST:
            return List[str], []
        return Any, None

    def _get_default_value(self, field_def: FieldDefinition) -> Any:
        ft = field_def.field_type
        if ft == FieldType.NUMBER:
            return field_def.default_value or 0
        elif ft == FieldType.POOL:
            return PoolValue(
                current=field_def.default_value or 10, max=field_def.default_value or 10
            )
        elif ft == FieldType.TRACK:
            return [False] * (field_def.track_length or 4)
        elif ft == FieldType.DIE:
            return field_def.die_default or "d6"
        elif ft == FieldType.LADDER:
            return LadderValue(value=field_def.default_value or 0)
        elif ft == FieldType.TAG:
            return ""
        elif ft == FieldType.TEXT:
            return ""
        elif ft == FieldType.LIST:
            return []
        return None

    # -------------------------------------------------------------------------
    # DATA CONVERSION
    # -------------------------------------------------------------------------
    def convert_simplified_to_full(
        self, simplified_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for role_key, role_data in simplified_data.items():
            if not isinstance(role_data, dict):
                result[role_key] = role_data
                continue

            result[role_key] = {}
            try:
                role = SemanticRole(role_key)
                role_fields = self.vocab.get_fields_by_role(role)
            except ValueError:
                role_fields = {}

            for field_key, field_value in role_data.items():
                field_def = role_fields.get(field_key)
                if field_def:
                    result[role_key][field_key] = self._expand_value(
                        field_def, field_value
                    )
                else:
                    result[role_key][field_key] = field_value
        return result

    def _expand_value(self, field_def: FieldDefinition, value: Any) -> Any:
        ft = field_def.field_type
        if ft == FieldType.POOL:
            if isinstance(value, (int, float)):
                return {"current": int(value), "max": int(value)}
        elif ft == FieldType.TRACK:
            length = field_def.track_length or 4
            if isinstance(value, int):
                return [i < value for i in range(length)]
        elif ft == FieldType.LADDER:
            if isinstance(value, int):
                label = (
                    field_def.ladder_labels.get(value, "")
                    if field_def.ladder_labels
                    else ""
                )
                return {"value": value, "label": label}
        elif ft == FieldType.LIST:
            if isinstance(value, list) and all(isinstance(x, str) for x in value):
                return [{"name": x, "qty": 1} for x in value]
        return value

    def get_creation_prompt_hints(self) -> str:
        return self.vocab.get_field_hints_for_prompt()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def build_character_model_from_vocabulary(vocab: GameVocabulary) -> Type[BaseModel]:
    builder = SchemaBuilder(vocab)
    return builder.build_character_model()


def build_creation_model_from_vocabulary(vocab: GameVocabulary) -> Type[BaseModel]:
    builder = SchemaBuilder(vocab)
    return builder.build_creation_prompt_model()


def get_creation_hints_from_vocabulary(vocab: GameVocabulary) -> str:
    builder = SchemaBuilder(vocab)
    return builder.get_creation_prompt_hints()
