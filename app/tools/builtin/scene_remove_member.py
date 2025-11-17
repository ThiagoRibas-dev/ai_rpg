# app/tools/builtin/scene_remove_member.py
from typing import Any
from app.tools.builtin._state_storage import get_entity, set_entity

def handler(character_key: str, **context: Any) -> dict:
    """
    Removes a character from the active scene, for example when they leave
    the area or are defeated.
    """
    session_id = context.get("session_id")
    db = context.get("db_manager")
    
    if not session_id or not db:
        raise ValueError("Missing session context for scene.remove_member.")

    scene = get_entity(session_id, db, "scene", "active_scene")
    if not scene:
        return {"success": False, "error": "No active scene to remove member from."}

    member_id = f"character:{character_key}"
    members = scene.get("members", [])
    if member_id in members:
        members.remove(member_id)
        scene["members"] = members
        set_entity(session_id, db, "scene", "active_scene", scene)
        return {"success": True, "scene": "active_scene", "member_removed": member_id}
    
    return {"success": False, "note": f"Member '{member_id}' was not in the active scene."}
