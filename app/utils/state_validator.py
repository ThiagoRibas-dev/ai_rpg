import logging
from typing import Any
from app.models.stat_block import StatBlockTemplate

logger = logging.getLogger(__name__)

class ValidationError(ValueError):
    pass

class StateValidator:
    """Validates against Functional Schema (Values/Gauges/Collections)."""

    def __init__(self, template: StatBlockTemplate):
        self.template = template

    def validate_update(self, key: str, value: Any) -> str:
        # Check Values
        if key in self.template.values:
            return "value"

        # Check Gauges
        if key in self.template.gauges:
            return "gauge"

        # Check Collections
        if key in self.template.collections:
            return "collection"

        raise ValidationError(f"Property '{key}' not found in template.")
