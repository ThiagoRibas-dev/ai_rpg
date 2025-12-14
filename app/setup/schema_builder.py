"""
Schema Builder
==============
Dynamically generates Pydantic models from a GameVocabulary.

This is the bridge between the vocabulary (what fields exist) and runtime
schemas (how to validate data). All generated schemas are guaranteed to
align with the vocabulary.

Use Cases:
1. Character Creation: Generate models for LLM to fill in character data
2. Entity Updates: Generate models for validating tool arguments
3. Invariant Validation: Provide type information for validators
4. UI Rendering: Generate field metadata for dynamic UI

Key Principle:
  The vocabulary defines WHAT exists.
  The schema builder defines HOW to represent it in code.
"""

import logging
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel, Field, create_model

from app.models.vocabulary import (
    GameVocabulary,
    FieldDefinition,
    FieldType,
    SemanticRole,
)

logger = logging.getLogger(__name__)


# =============================================================================
# TYPE MAPPINGS
# =============================================================================

# Default Python types for each field type
FIELD_TYPE_TO_PYTHON = {
    FieldType.NUMBER: int,
    FieldType.POOL: Dict[str, int],  # {"current": x, "max": y}
    FieldType.TRACK: List[bool],  # [True, False, False, True]
    FieldType.DIE: str,  # "d8", "2d6"
    FieldType.LADDER: Dict[str, Any],  # {"value": 2, "label": "Good"}
    FieldType.TAG: str,  # Simple string for basic usage
    FieldType.TEXT: str,
    FieldType.LIST: List[Dict[str, Any]],  # Array of items
}


# =============================================================================
# SUB-MODELS (Reusable building blocks)
# =============================================================================


class PoolValue(BaseModel):
    """A resource with current and max values."""

    current: int = 0
    max: int = 10

    class Config:
        extra = "allow"


class LadderValue(BaseModel):
    """A rating on a named ladder (Fate-style)."""

    value: int = 0
    label: str = ""

    class Config:
        extra = "allow"


class TagValue(BaseModel):
    """A narrative tag with optional metadata."""

    text: str = ""
    free_invokes: int = 0

    class Config:
        extra = "allow"


class InventoryItem(BaseModel):
    """A generic inventory item."""

    name: str = ""
    description: str = ""
    quantity: int = 1

    class Config:
        extra = "allow"


# =============================================================================
# SCHEMA BUILDER
# =============================================================================


class SchemaBuilder:
    """
    Dynamically generates Pydantic models from a GameVocabulary.

    All generated models are cached for performance.
    Models are guaranteed to align with vocabulary paths.

    Example:
        vocab = extract_vocabulary_from_text(llm, rules)
        builder = SchemaBuilder(vocab)

        CharacterModel = builder.build_character_model()
        character = CharacterModel(...)  # Validated against vocab structure
    """

    def __init__(self, vocabulary: GameVocabulary):
        self.vocab = vocabulary
        self._cache: Dict[str, Type[BaseModel]] = {}

    # =========================================================================
    # MAIN BUILDERS
    # =========================================================================

    def build_character_model(self) -> Type[BaseModel]:
        """
        Generate a complete Character model from vocabulary.

        The model has one attribute per semantic role that has fields.
        Each attribute is itself a model containing the role's fields.

        Returns:
            A Pydantic model class for character data
        """
        cache_key = "character"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Build sub-models for each semantic role
        role_models: Dict[str, Any] = {}

        for role in SemanticRole:
            role_fields = self.vocab.get_fields_by_role(role)
            if not role_fields:
                continue

            # Build the role's model
            role_model = self._build_role_model(role, role_fields)
            role_models[role.value] = (role_model, Field(default_factory=role_model))

        # Always include identity
        if "identity" not in role_models:
            identity_model = self._build_identity_model()
            role_models["identity"] = (
                identity_model,
                Field(default_factory=identity_model),
            )

        # Create the character model
        CharacterModel = create_model(
            "Character",
            __config__=type("Config", (), {"extra": "allow"}),
            **role_models,
        )

        self._cache[cache_key] = CharacterModel
        return CharacterModel

    def build_entity_data_model(self) -> Type[BaseModel]:
        """
        Generate a flat model for entity data storage.

        This is used for the actual stored entity data, which uses
        a flatter structure than the nested character model.

        Returns:
            A Pydantic model for entity data
        """
        cache_key = "entity_data"
        if cache_key in self._cache:
            return self._cache[cache_key]

        fields: Dict[str, Any] = {}

        # Add identity fields
        fields["name"] = (str, Field(default=""))
        fields["description"] = (str, Field(default=""))
        fields["template_id"] = (Optional[int], None)

        # Add fields organized by role
        for role in SemanticRole:
            if self.vocab.get_fields_by_role(role):
                fields[role.value] = (
                    Optional[Dict[str, Any]],
                    Field(default_factory=dict),
                )

        EntityDataModel = create_model(
            "EntityData", __config__=type("Config", (), {"extra": "allow"}), **fields
        )

        self._cache[cache_key] = EntityDataModel
        return EntityDataModel

    def build_update_model(self) -> Type[BaseModel]:
        """
        Generate a model for entity update arguments.

        Used to validate the 'updates' argument of entity.update tool.
        All fields are optional since updates are partial.

        Returns:
            A Pydantic model for update validation
        """
        cache_key = "update"
        if cache_key in self._cache:
            return self._cache[cache_key]

        fields: Dict[str, Any] = {}

        # Add all valid paths as optional fields
        for path in self.vocab.valid_paths:
            # Convert path to valid Python identifier
            field_name = path.replace(".", "_")

            # Determine type from field definition
            field_def = self.vocab.get_field_by_path(path)
            if field_def:
                py_type = self._get_python_type_for_update(field_def, path)
            else:
                py_type = Any

            fields[field_name] = (Optional[py_type], None)

        UpdateModel = create_model(
            "EntityUpdate", __config__=type("Config", (), {"extra": "allow"}), **fields
        )

        self._cache[cache_key] = UpdateModel
        return UpdateModel

    def build_creation_prompt_model(self) -> Type[BaseModel]:
        """
        Generate a model optimized for LLM character creation.

        This model uses simpler types that are easier for LLMs to fill:
        - Pools become {current: int, max: int}
        - Tracks become List[bool]
        - Ladders become int (the value only)

        Returns:
            A Pydantic model for character creation prompts
        """
        cache_key = "creation_prompt"
        if cache_key in self._cache:
            return self._cache[cache_key]

        role_models: Dict[str, Any] = {}

        for role in SemanticRole:
            role_fields = self.vocab.get_fields_by_role(role)
            if not role_fields:
                continue

            # Build simplified role model
            simplified = self._build_simplified_role_model(role, role_fields)
            role_models[role.value] = (simplified, Field(default_factory=simplified))

        # Always include identity
        if "identity" not in role_models:
            identity = self._build_identity_model()
            role_models["identity"] = (identity, Field(default_factory=identity))

        CreationModel = create_model(
            "CharacterCreation",
            __config__=type("Config", (), {"extra": "allow"}),
            **role_models,
        )

        self._cache[cache_key] = CreationModel
        return CreationModel

    # =========================================================================
    # ROLE BUILDERS
    # =========================================================================

    def _build_role_model(
        self, role: SemanticRole, fields: Dict[str, FieldDefinition]
    ) -> Type[BaseModel]:
        """Build a model for a semantic role's fields."""
        model_fields: Dict[str, Any] = {}

        for key, field_def in fields.items():
            py_type = self._get_python_type(field_def)
            default = self._get_default_value(field_def)

            if default is None:
                model_fields[key] = (Optional[py_type], None)
            else:
                model_fields[key] = (py_type, Field(default=default))

        model_name = f"{role.value.title().replace('_', '')}Fields"
        return create_model(
            model_name,
            __config__=type("Config", (), {"extra": "allow"}),
            **model_fields,
        )

    def _build_simplified_role_model(
        self, role: SemanticRole, fields: Dict[str, FieldDefinition]
    ) -> Type[BaseModel]:
        """Build a simplified model for LLM prompts."""
        model_fields: Dict[str, Any] = {}

        for key, field_def in fields.items():
            py_type, default = self._get_simplified_type_and_default(field_def)

            if default is None:
                model_fields[key] = (Optional[py_type], None)
            else:
                model_fields[key] = (py_type, Field(default=default))

        model_name = f"{role.value.title().replace('_', '')}Creation"
        return create_model(
            model_name,
            __config__=type("Config", (), {"extra": "allow"}),
            **model_fields,
        )

    def _build_identity_model(self) -> Type[BaseModel]:
        """Build the standard identity model."""
        return create_model(
            "Identity",
            __config__=type("Config", (), {"extra": "allow"}),
            name=(str, Field(default="")),
            description=(str, Field(default="")),
            concept=(str, Field(default="")),
            player_name=(str, Field(default="")),
        )

    # =========================================================================
    # TYPE RESOLUTION
    # =========================================================================

    def _get_python_type(self, field_def: FieldDefinition) -> Type:
        """Get the Python type for a field definition."""
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
        else:
            return Any

    def _get_python_type_for_update(
        self, field_def: FieldDefinition, path: str
    ) -> Type:
        """Get the Python type for a specific update path."""
        ft = field_def.field_type

        # Check if this is a sub-path (e.g., resource.hp.current)
        parts = path.split(".")
        if len(parts) > 2:
            sub_key = parts[-1]

            # Pool sub-paths
            if ft == FieldType.POOL and sub_key in ("current", "max"):
                return int

            # Track sub-paths
            if ft == FieldType.TRACK:
                if sub_key == "filled":
                    return int
                elif sub_key.isdigit():
                    return bool

            # Ladder sub-paths
            if ft == FieldType.LADDER:
                if sub_key == "value":
                    return int
                elif sub_key == "label":
                    return str

        # Full field updates
        return self._get_python_type(field_def)

    def _get_simplified_type_and_default(
        self, field_def: FieldDefinition
    ) -> tuple[Type, Any]:
        """
        Get simplified type and default for LLM prompts.

        Makes types simpler for LLM to understand and fill.
        """
        ft = field_def.field_type

        if ft == FieldType.NUMBER:
            default = field_def.default_value
            if default is None:
                default = (
                    10 if field_def.semantic_role == SemanticRole.CORE_TRAIT else 0
                )
            return int, default

        elif ft == FieldType.POOL:
            # Simplified: just ask for max, current defaults to max
            return int, field_def.default_value or 10

        elif ft == FieldType.TRACK:
            # Simplified: number of boxes filled
            return int, 0

        elif ft == FieldType.DIE:
            return str, field_def.die_default or "d6"

        elif ft == FieldType.LADDER:
            # Simplified: just the numeric value
            return int, field_def.default_value or 0

        elif ft == FieldType.TAG:
            return str, ""

        elif ft == FieldType.TEXT:
            return str, ""

        elif ft == FieldType.LIST:
            return List[str], []  # Simplified: list of names

        else:
            return Any, None

    def _get_default_value(self, field_def: FieldDefinition) -> Any:
        """Get the default value for a field."""
        ft = field_def.field_type

        if ft == FieldType.NUMBER:
            return field_def.default_value or 0

        elif ft == FieldType.POOL:
            max_val = field_def.default_value or 10
            return PoolValue(current=max_val, max=max_val)

        elif ft == FieldType.TRACK:
            length = field_def.track_length or 4
            return [False] * length

        elif ft == FieldType.DIE:
            return field_def.die_default or "d6"

        elif ft == FieldType.LADDER:
            value = field_def.default_value or 0
            label = ""
            if field_def.ladder_labels and value in field_def.ladder_labels:
                label = field_def.ladder_labels[value]
            return LadderValue(value=value, label=label)

        elif ft == FieldType.TAG:
            return ""

        elif ft == FieldType.TEXT:
            return ""

        elif ft == FieldType.LIST:
            return []

        else:
            return None

    # =========================================================================
    # PROMPT GENERATION
    # =========================================================================

    def get_creation_prompt_hints(self) -> str:
        """
        Generate detailed hints for LLM character creation.

        Includes field types, ranges, and examples.
        """
        lines = ["# Character Creation Guide\n"]
        lines.append(f"System: {self.vocab.system_name}\n")

        for role in SemanticRole:
            role_fields = self.vocab.get_fields_by_role(role)
            if not role_fields:
                continue

            lines.append(f"## {role.value.replace('_', ' ').title()}\n")

            for key, field_def in role_fields.items():
                hint = self._format_field_hint(field_def)
                lines.append(f"- **{field_def.label}** (`{key}`): {hint}")

            lines.append("")

        return "\n".join(lines)

    def _format_field_hint(self, field_def: FieldDefinition) -> str:
        """Format a hint string for a single field."""
        ft = field_def.field_type
        parts = []

        # Type description
        type_desc = {
            FieldType.NUMBER: "integer",
            FieldType.POOL: "value (will create current/max pool)",
            FieldType.TRACK: "number of boxes filled",
            FieldType.DIE: "die notation (e.g., 'd8', '2d6')",
            FieldType.LADDER: "rating value",
            FieldType.TAG: "descriptive text",
            FieldType.TEXT: "free text",
            FieldType.LIST: "list of names",
        }
        parts.append(type_desc.get(ft, "value"))

        # Range
        if field_def.min_value is not None or field_def.max_value is not None:
            min_v = field_def.min_value if field_def.min_value is not None else "?"
            max_v = field_def.max_value if field_def.max_value is not None else "?"
            parts.append(f"range {min_v}-{max_v}")

        # Ladder labels
        if ft == FieldType.LADDER and field_def.ladder_labels:
            labels = [
                f"{v}={k}" for k, v in sorted(field_def.ladder_labels.items())[:4]
            ]
            parts.append(f"labels: {', '.join(labels)}")

        # Track length
        if ft == FieldType.TRACK:
            parts.append(f"{field_def.track_length or 4} boxes")

        # Default
        if field_def.default_value is not None:
            parts.append(f"default: {field_def.default_value}")

        # Description
        if field_def.description:
            parts.append(field_def.description)

        return " | ".join(parts)

    def get_update_path_documentation(self) -> str:
        """
        Generate documentation of valid update paths.

        Used in tool descriptions and error messages.
        """
        lines = ["# Valid Update Paths\n"]

        # Group by role
        paths_by_role: Dict[str, List[str]] = {}
        for path in self.vocab.valid_paths:
            parts = path.split(".")
            if parts:
                role = parts[0]
                if role not in paths_by_role:
                    paths_by_role[role] = []
                paths_by_role[role].append(path)

        for role, paths in sorted(paths_by_role.items()):
            lines.append(f"## {role}\n")
            for path in sorted(paths)[:10]:  # Limit for readability
                field_def = self.vocab.get_field_by_path(path)
                type_hint = ""
                if field_def:
                    type_hint = f" ({field_def.field_type.value})"
                lines.append(f"- `{path}`{type_hint}")

            if len(paths) > 10:
                lines.append(f"- ... and {len(paths) - 10} more")
            lines.append("")

        return "\n".join(lines)

    # =========================================================================
    # DATA CONVERSION
    # =========================================================================

    def convert_simplified_to_full(
        self, simplified_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Convert simplified creation data to full entity format.

        Expands:
        - Pool integers to {current, max}
        - Track integers to boolean arrays
        - Ladder integers to {value, label}
        """
        result: Dict[str, Any] = {}

        for role_key, role_data in simplified_data.items():
            if not isinstance(role_data, dict):
                result[role_key] = role_data
                continue

            result[role_key] = {}
            role_fields = (
                self.vocab.get_fields_by_role(
                    SemanticRole(role_key)
                    if role_key in [r.value for r in SemanticRole]
                    else None
                )
                if role_key in [r.value for r in SemanticRole]
                else {}
            )

            for field_key, field_value in role_data.items():
                field_def = role_fields.get(field_key) if role_fields else None

                if field_def:
                    result[role_key][field_key] = self._expand_value(
                        field_def, field_value
                    )
                else:
                    result[role_key][field_key] = field_value

        return result

    def _expand_value(self, field_def: FieldDefinition, value: Any) -> Any:
        """Expand a simplified value to full format."""
        ft = field_def.field_type

        if ft == FieldType.POOL:
            # Integer becomes {current: value, max: value}
            if isinstance(value, (int, float)):
                return {"current": int(value), "max": int(value)}
            elif isinstance(value, dict):
                return value
            else:
                return {"current": 10, "max": 10}

        elif ft == FieldType.TRACK:
            # Integer becomes array with that many True values
            length = field_def.track_length or 4
            if isinstance(value, int):
                return [i < value for i in range(length)]
            elif isinstance(value, list):
                # Pad or truncate to correct length
                result = list(value) + [False] * length
                return result[:length]
            else:
                return [False] * length

        elif ft == FieldType.LADDER:
            # Integer becomes {value, label}
            if isinstance(value, int):
                label = ""
                if field_def.ladder_labels and value in field_def.ladder_labels:
                    label = field_def.ladder_labels[value]
                return {"value": value, "label": label}
            elif isinstance(value, dict):
                return value
            else:
                return {"value": 0, "label": ""}

        else:
            return value

    # =========================================================================
    # UTILITY
    # =========================================================================

    def clear_cache(self):
        """Clear the model cache."""
        self._cache.clear()

    def get_cache_stats(self) -> Dict[str, int]:
        """Get statistics about cached models."""
        return {
            "cached_models": len(self._cache),
            "model_names": list(self._cache.keys()),
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def build_character_model_from_vocabulary(vocab: GameVocabulary) -> Type[BaseModel]:
    """Convenience function to build a character model."""
    builder = SchemaBuilder(vocab)
    return builder.build_character_model()


def build_creation_model_from_vocabulary(vocab: GameVocabulary) -> Type[BaseModel]:
    """Convenience function to build a creation model."""
    builder = SchemaBuilder(vocab)
    return builder.build_creation_prompt_model()


def get_creation_hints_from_vocabulary(vocab: GameVocabulary) -> str:
    """Convenience function to get creation hints."""
    builder = SchemaBuilder(vocab)
    return builder.get_creation_prompt_hints()
