# File: app/utils/state_validator.py
import logging
import re
from typing import Any
from app.models.stat_block import StatBlockTemplate, AbilityDef, VitalDef, TrackDef

logger = logging.getLogger(__name__)


class ValidationError(ValueError):
    """Custom exception for state validation errors."""
    pass


class StateValidator:
    """
    Validates entity data against the schemas defined in the session's manifest.
    """

    def __init__(self, template: StatBlockTemplate):
        if not template:
            raise ValueError("StateValidator initialized without a StatBlockTemplate.")
        self.template = template

    def validate_update(self, key: str, value: Any) -> str:
        """
        Validates a single key-value update against the template.
        Returns the category of the property ("ability", "vital", "track") or raises ValidationError.
        """
        # 1. Check Abilities
        ability = next((a for a in self.template.abilities if a.name == key or a.abbr == key), None)
        if ability:
            self._validate_ability(ability, value)
            return "ability"
        
        # 2. Check Vitals
        vital = next((v for v in self.template.vitals if v.name == key), None)
        if vital:
            self._validate_vital(vital, value)
            return "vital"
        
        # 3. Check Tracks
        track = next((t for t in self.template.tracks if t.name == key), None)
        if track:
            self._validate_track(track, value)
            return "track"
        
        # If unknown, fail strict validation (or log warning in lax mode)
        raise ValidationError(f"Property '{key}' is not defined in the StatBlockTemplate '{self.template.template_name}'.")

    def _validate_ability(self, definition: AbilityDef, value: Any):
        # Data Type Check
        if definition.data_type == "integer":
            if not isinstance(value, int):
                raise ValidationError(f"Ability '{definition.name}' expects integer, got {type(value).__name__}")
            # Range Check
            if definition.range_min is not None and value < definition.range_min:
                raise ValidationError(f"{definition.name} cannot be less than {definition.range_min}")
            if definition.range_max is not None and value > definition.range_max:
                raise ValidationError(f"{definition.name} cannot exceed {definition.range_max}")
                
        elif definition.data_type == "die_code":
            if not isinstance(value, str):
                raise ValidationError(f"Ability '{definition.name}' expects die code string, got {type(value).__name__}")
            # Simple Regex for d4, d6, d8, d10, d12, d20, d100
            if not re.match(r"^d(4|6|8|10|12|20|100)$", value):
                raise ValidationError(f"Invalid die code '{value}'. Expected standard die (e.g., 'd6', 'd20').")
                
        elif definition.data_type == "dots":
            if not isinstance(value, int):
                 raise ValidationError(f"Ability '{definition.name}' (dots) expects integer, got {type(value).__name__}")
            if not (0 <= value <= 5): # Hardcoded standard for dots, could use range_max
                 raise ValidationError(f"Dots for {definition.name} must be between 0 and 5.")
 
        elif definition.data_type == "string":
            if not isinstance(value, str):
                raise ValidationError(f"Ability '{definition.name}' expects string, got {type(value).__name__}")
    def _validate_vital(self, definition: VitalDef, value: Any):
        # Vitals can be updated as a single number (current) or a dict {current, max}
        if isinstance(value, (int, float)):
            if value < definition.min_value:
                raise ValidationError(f"{definition.name} cannot be less than {definition.min_value}")
            # Note: Max validation is tricky without evaluating the formula. 
            # We assume the Tool Handler might handle max clamping if it knows the current max.
            # Here we just validate type.
        elif isinstance(value, dict):
            if "current" in value and not isinstance(value["current"], (int, float)):
                 raise ValidationError(f"Vital '{definition.name}.current' must be a number.")
            if "max" in value and not isinstance(value["max"], (int, float)):
                 raise ValidationError(f"Vital '{definition.name}.max' must be a number.")
        else:
            raise ValidationError(f"Vital update for '{definition.name}' must be a number or dict.")

    def _validate_track(self, definition: TrackDef, value: Any):
        # Track value is an integer step
        if not isinstance(value, int):
            raise ValidationError(f"Track '{definition.name}' expects integer value.")
        
        if value < 0:
            raise ValidationError(f"Track '{definition.name}' cannot be negative.")
        if value > definition.max_value:
            raise ValidationError(f"Track '{definition.name}' cannot exceed {definition.max_value}.")
