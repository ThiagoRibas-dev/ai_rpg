# app/tools/builtin/scene_move_to.py
import logging
from typing import Any
from app.tools.builtin._state_storage import get_entity, set_entity
from app.tools.builtin.state_apply_patch import handler as apply_patch

logger = logging.getLogger(__name__)

def handler(new_location_key: str, **context: Any) -> dict:
    """
    Atomically moves all members of the active scene to a new location.
    This updates the scene entity itself and also patches each individual
    character entity to maintain state consistency.
    """
    session_id = context.get("session_id")
    db = context.get("db_manager")

    if not session_id or not db:
        raise ValueError("Missing session context for scene.move_to.")

    scene = get_entity(session_id, db, "scene", "active_scene")
    if not scene:
        return {"success": False, "error": "No active scene to move."}

    members_to_move = scene.get("members", [])
    
    # 1. Update the location for each member individually
    for member_id_str in members_to_move:
        try:
            entity_type, entity_key = member_id_str.split(":", 1)
            if entity_type == "character":
                patch = [{"op": "replace", "path": "/location_key", "value": new_location_key}]
                apply_patch("character", entity_key, patch, **context)
        except Exception as e:
            logger.warning(f"Could not move member '{member_id_str}': {e}")
    
    # 2. Update the scene's location
    scene["location_key"] = new_location_key
    set_entity(session_id, db, "scene", "active_scene", scene)

    return {"success": True, "new_location": new_location_key, "members_moved": len(members_to_move)}
