# File: app/utils/state_validator.py
# --- NEW FILE ---

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ValidationError(ValueError):
    """Custom exception for state validation errors."""
    pass


class StateValidator:
    """
    Validates entity data against the schemas defined in the session's manifest.
    """

    def __init__(self, manifest: Dict[str, Any]):
        if not manifest:
            raise ValueError("StateValidator cannot be initialized with an empty manifest.")
        self.manifest = manifest

    def validate_entity(self, entity_type: str, data: Dict[str, Any]):
        """
        Validates a full entity data dictionary against the manifest.
        Raises ValidationError on failure.
        """
        logger.debug(f"Validating entity of type '{entity_type}'...")
        
        # For now, we are most concerned with validating character properties,
        # as this is where the AI has the most freedom.
        if entity_type == "character":
            self._validate_character_properties(data)

        # Future validation for other entity types (items, locations) can be added here.
        logger.debug(f"Validation successful for entity '{entity_type}'.")

    def _get_property_definition(self, prop_name: str) -> Dict[str, Any] | None:
        """Finds the definition for a custom property in the manifest."""
        char_schema = self.manifest.get("entity_schemas", {}).get("character", {})
        
        for attr_def in char_schema.get("attributes", []):
            if attr_def.get("name") == prop_name:
                return attr_def
        
        for res_def in char_schema.get("resources", []):
            if res_def.get("name") == prop_name:
                return res_def
                
        return None

    def _validate_character_properties(self, data: Dict[str, Any]):
        """
        Validates the 'properties' block of a character entity.
        """
        properties = data.get("properties", {})
        if not isinstance(properties, dict):
            raise ValidationError("Character 'properties' field must be a dictionary.")

        for prop_name, prop_value in properties.items():
            prop_def = self._get_property_definition(prop_name)

            # It's okay for an entity to have properties not in the manifest (e.g., 'race', 'class'),
            # but if a definition DOES exist, we must enforce it.
            if not prop_def:
                continue

            # Type Validation
            prop_type = prop_def.get("type")
            if prop_type == "integer" and not isinstance(prop_value, int):
                raise ValidationError(f"Property '{prop_name}' must be an integer, but got '{type(prop_value).__name__}'.")
            elif prop_type == "string" and not isinstance(prop_value, str):
                raise ValidationError(f"Property '{prop_name}' must be a string, but got '{type(prop_value).__name__}'.")

            # Range Validation (for integers/resources)
            if prop_type in ["integer", "attribute", "resource"]:
                prop_range = prop_def.get("range")
                if prop_range and len(prop_range) == 2:
                    min_val, max_val = prop_range
                    if not (min_val <= prop_value <= max_val):
                        raise ValidationError(f"Value for '{prop_name}' ({prop_value}) is outside the allowed range of [{min_val}, {max_val}].")

            # Enum Validation
            if prop_type == "enum":
                allowed = prop_def.get("allowed_values")
                if allowed and prop_value not in allowed:
                    raise ValidationError(f"Value for '{prop_name}' ('{prop_value}') is not one of the allowed values: {allowed}.")


def get_python_type(type_str: str) -> type:
    """Maps schema type strings to Python types."""
    return {
        "integer": int,
        "string": str,
        "boolean": bool,
        "enum": str,
    }.get(type_str, object)
