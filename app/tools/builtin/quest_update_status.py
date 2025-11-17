from typing import Any
from app.tools.builtin.state_apply_patch import handler as apply_patch


def handler(
    quest_key: str,
    new_status: str,
    **context: Any,
) -> dict:
    """
    Handler for quest.update_status. Translates the call into a simple
    state.apply_patch operation.
    """
    patch = [{"op": "replace", "path": "/status", "value": new_status}]
    
    result = apply_patch("quest", quest_key, patch, **context)
    result.update({"quest_key": quest_key, "new_status": new_status})
    return result
