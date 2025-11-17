# app/tools/builtin/scene_add_member.py
from typing import Any
from app.tools.builtin._state_storage import get_entity, set_entity

def handler(character_key: str, **context: Any) -> dict:
    """
    Adds a character to the active scene, ensuring they are tracked for
    contextual memory retrieval and group actions.
    """
    session_id = context.get("session_id")
    db = context.get("db_manager")
    
    if not session_id or not db:
        raise ValueError("Missing session context for scene.add_member.")

    scene = get_entity(session_id, db, "scene", "active_scene")
    if not scene:
        # If no scene exists, create a default one centered on the player
        player = get_entity(session_id, db, "character", "player")
        scene = {
            "location_key": player.get("location_key", "unknown"),
            "members": ["character:player"],
            "state_tags": ["calm"]
        }

    member_id = f"character:{character_key}"
    if member_id not in scene.get("members", []):
        scene.setdefault("members", []).append(member_id)

    set_entity(session_id, db, "scene", "active_scene", scene)
    
    return {"success": True, "scene": "active_scene", "member_added": member_id}
