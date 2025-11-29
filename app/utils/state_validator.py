import logging
from typing import Any
from app.models.stat_block import StatBlockTemplate

logger = logging.getLogger(__name__)


class ValidationError(ValueError):
    pass


class StateValidator:
    """Validates against Refined Schema."""

    def __init__(self, template: StatBlockTemplate):
        self.template = template

    def validate_update(self, key: str, value: Any) -> str:
        # Fundamental Stats
        fund = next((a for a in self.template.fundamental_stats if a.name == key), None)
        if fund:
            return "fundamental_stat"

        # Vitals
        vit = next((s for s in self.template.vital_resources if s.name == key), None)
        if vit:
            return "vital"

        # Consumables
        con = next(
            (a for a in self.template.consumable_resources if a.name == key), None
        )
        if con:
            return "consumable"

        # Skills
        skill = next((s for s in self.template.skills if s.name == key), None)
        if skill:
            return "skill"

        raise ValidationError(f"Property '{key}' not found in template.")
