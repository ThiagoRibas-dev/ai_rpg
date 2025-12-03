from typing import Any

class ValidationError(ValueError):
    pass

class StateValidator:
    """
    Permissive validator for Dynamic Sheets.
    Since the schema creates the UI, we assume updates coming from the UI or LLM
    are generally intending to modify the correct path.
    """
    def __init__(self, template: Any):
        self.template = template

    def validate_update(self, key: str, value: Any) -> str:
        # In the dynamic system, we allow updates to flow through.
        # The renderer handles missing keys gracefully.
        return "dynamic"
