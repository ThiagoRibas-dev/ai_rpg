import logging
from typing import Any, Dict, List


from app.models.entities import Character
from app.models.property_definition import PropertyDefinition
from app.tools.builtin._state_storage import get_entity, set_entity

logger = logging.getLogger(__name__)

def _get_python_type(type_str: str) -> type:
    """Maps schema type strings to Python types."""
    return {
        "integer": int,
        "string": str,
        "boolean": bool,
        "enum": str,
        "resource": int
    }.get(type_str, object)

def _is_core_attribute(char: Character, key: str) -> bool:
    """Checks if a key corresponds to a core attribute of the Character model."""
    return key in char.model_fields or (hasattr(char, 'attributes') and key in char.attributes.model_fields)

def _update_core_attribute(char: Character, key: str, value: Any):
    """Updates a core attribute of the Character model."""
    if key in char.model_fields:
        setattr(char, key, value)
    elif hasattr(char, 'attributes') and key in char.attributes.model_fields:
        setattr(char.attributes, key, value)
    else:
        raise ValueError(f"Core attribute '{key}' not found on Character or CharacterAttributes.")

def _update_custom_property(char: Character, key: str, value: Any, schema_defs: Dict[str, PropertyDefinition]):
    """Updates a custom property with validation against its schema definition."""
    if key not in schema_defs:
        logger.warning(f"Setting undefined custom property: {key}. No validation applied.")
        char.properties[key] = value
        return

    prop_def = schema_defs[key]

    # Type validation
    expected_type = _get_python_type(prop_def.type)
    if not isinstance(value, expected_type):
        raise TypeError(f"Property '{key}' must be of type '{prop_def.type}', but received '{type(value).__name__}'.")

    # Range validation for integer/resource types
    if prop_def.type in ["integer", "resource"]:
        if prop_def.min_value is not None and value < prop_def.min_value:
            raise ValueError(f"Property '{key}' cannot be less than {prop_def.min_value}. Received {value}.")
        if prop_def.max_value is not None and value > prop_def.max_value:
            raise ValueError(f"Property '{key}' cannot exceed {prop_def.max_value}. Received {value}.")

    # Enum validation
    if prop_def.type == "enum" and prop_def.allowed_values is not None and value not in prop_def.allowed_values:
        raise ValueError(f"Property '{key}' must be one of {prop_def.allowed_values}. Received '{value}'.")

    char.properties[key] = value

def _apply_game_logic(char: Character):
    """Applies game logic based on character state changes, e.g., death detection."""
    if char.attributes.hp_current <= 0:
        if "unconscious" not in char.conditions:
            char.conditions.append("unconscious")
        if char.attributes.hp_current <= -char.attributes.hp_max:
            if "dead" not in char.conditions:
                char.conditions.append("dead")
    else:
        # Remove death conditions if healed
        char.conditions = [c for c in char.conditions if c not in ("unconscious", "dead")]

def handler(character_key: str, updates: List[Dict[str, Any]], **context) -> dict:
    """
    Handler for the character.update tool.
    Updates character attributes and properties with validation.
    """
    session_id = context["session_id"]
    db = context["db_manager"]

    # Load entity
    char_data = get_entity(session_id, db, "character", character_key)

    if not char_data:
        raise ValueError(f"Character '{character_key}' not found.")

    # Load into Pydantic model for validation
    try:
        char = Character(**char_data)
    except Exception as e:
        raise ValueError(f"Invalid character data loaded from DB: {e}")

    # Load schema definitions for custom properties
    schema_defs_raw = db.get_schema_extensions(session_id, "character")
    schema_defs = {name: PropertyDefinition(**data) for name, data in schema_defs_raw.items()}

    # Apply updates with validation
    for update_pair in updates:
        key = update_pair["key"]
        value = update_pair["value"]
        try:
            if _is_core_attribute(char, key):
                _update_core_attribute(char, key, value)
            else:
                _update_custom_property(char, key, value, schema_defs)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Validation failed for property '{key}': {e}")

    # Apply game logic hooks
    _apply_game_logic(char)

    # Save back
    version = set_entity(session_id, db, "character", character_key, char.model_dump())

    return {
        "success": True,
        "character_key": character_key,
        "updated_fields": [upd["key"] for upd in updates],
        "version": version
    }
