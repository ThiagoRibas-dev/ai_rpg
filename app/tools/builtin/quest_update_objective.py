from typing import Any
from app.tools.builtin._state_storage import get_entity
from app.tools.builtin.state_apply_patch import handler as apply_patch


def handler(
    quest_key: str,
    objective_text: str,
    is_completed: bool = True,
    **context: Any,
) -> dict:
    """
    Handler for quest.update_objective. Finds the objective by text and
    patches its completion status.
    """
    quest = get_entity(context["session_id"], context["db_manager"], "quest", quest_key)

    if not quest or not quest.get("objectives"):
        return {"success": False, "error": f"Quest '{quest_key}' not found or has no objectives."}

    objectives = quest.get("objectives", [])
    
    for i, obj in enumerate(objectives):
        if obj.get("text", "").lower() == objective_text.lower():
            # Found the objective, now create a patch for it
            patch = [{"op": "replace", "path": f"/objectives/{i}/completed", "value": is_completed}]
            
            result = apply_patch("quest", quest_key, patch, **context)
            result.update({"quest_key": quest_key, "objective_index": i, "is_completed": is_completed})
            return result

    return {"success": False, "error": f"Objective '{objective_text}' not found in quest '{quest_key}'."}
