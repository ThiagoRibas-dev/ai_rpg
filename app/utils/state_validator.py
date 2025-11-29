import logging
from typing import Any
from app.models.stat_block import StatBlockTemplate

logger = logging.getLogger(__name__)

class ValidationError(ValueError):
    pass

class StateValidator:
    """Validates against Refined Schema (Dict-based)."""

    def __init__(self, template: StatBlockTemplate):
        self.template = template

    def validate_update(self, key: str, value: Any) -> str:
        # Check Keys in Dicts
        if key in self.template.fundamental_stats:
            return "fundamental_stat"

        if key in self.template.vital_resources:
            return "vital"

        if key in self.template.consumable_resources:
            return "consumable"

        if key in self.template.skills:
            return "skill"

        raise ValidationError(f"Property '{key}' not found in template.")
