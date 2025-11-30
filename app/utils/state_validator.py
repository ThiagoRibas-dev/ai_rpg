from typing import Any
from app.models.stat_block import StatBlockTemplate


class ValidationError(ValueError):
    pass


class StateValidator:
    def __init__(self, template: StatBlockTemplate):
        self.template = template

    def validate_update(self, key: str, value: Any) -> str:
        # 1. Fundamentals (Writeable)
        if key in self.template.fundamentals:
            return "fundamental"

        # 2. Derived (Technically read-only, but allowed for manual overrides)
        if key in self.template.derived:
            return "derived"

        # 3. Gauges (Writeable current)
        if key in self.template.gauges:
            return "gauge"

        # 4. Collections
        if key in self.template.collections:
            return "collection"

        raise ValidationError(f"Property '{key}' not found in template.")
