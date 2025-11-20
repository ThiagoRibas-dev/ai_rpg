from typing import Any
from app.tools.builtin._state_storage import get_entity, set_entity


def handler(
    quest_key: str,
    new_status: str,
    **context: Any,
) -> dict:
    """
    Handler for quest.update_status. Directly updates the entity.
    """
    session_id = context["session_id"]
    db = context["db_manager"]

    quest = get_entity(session_id, db, "quest", quest_key)
    if not quest:
        return {"success": False, "error": f"Quest '{quest_key}' not found."}
    
    quest["status"] = new_status
    version = set_entity(session_id, db, "quest", quest_key, quest)
    
    return {"success": True, "quest_key": quest_key, "new_status": new_status, "version": version}
