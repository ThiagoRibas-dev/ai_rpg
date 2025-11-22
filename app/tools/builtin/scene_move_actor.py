import logging
from typing import Dict, Any
from app.tools.builtin._state_storage import get_entity, set_entity

logger = logging.getLogger(__name__)

def handler(actor_key: str, target_zone_id: str, is_hidden: bool = False, **context) -> Dict[str, Any]:
    """
    Handles the scene.move_actor tool call.
    Moves a character to a specified zone within the active scene.
    """
    session_id = context.get("session_id")
    db_manager = context.get("db_manager")

    if not session_id or not db_manager:
        return {"error": "Missing session context"}

    try:
        character = get_entity(session_id, db_manager, "character", actor_key)
        if not character:
            return {"error": f"Character '{actor_key}' not found."}

        # Verify target_zone_id exists in active_scene's zones
        active_scene = get_entity(session_id, db_manager, "scene", "active_scene")
        if not active_scene:
            return {"error": "No active scene found. Cannot move actor."}
        
        zone_ids = [z["id"] for z in active_scene.get("zones", [])]
        if target_zone_id not in zone_ids:
            return {"error": f"Target zone '{target_zone_id}' not found in active scene zones."}

        # Update character's scene_state
        if "scene_state" not in character:
            character["scene_state"] = {}
        
        # Update values
        character["scene_state"]["zone_id"] = target_zone_id
        character["scene_state"]["is_hidden"] = is_hidden
        
        set_entity(session_id, db_manager, "character", actor_key, character)
        
        logger.info(f"Moved actor '{actor_key}' to zone '{target_zone_id}' (hidden: {is_hidden}).")
        
        # Trigger UI refresh for the scene map
        if context.get("ui_queue"):
            context["ui_queue"].put({"type": "turn_complete"})

        return {"success": True, "message": f"Actor '{actor_key}' moved to zone '{target_zone_id}'."}

    except Exception as e:
        logger.error(f"Error moving actor '{actor_key}' in scene {session_id}: {e}", exc_info=True)
        return {"error": str(e)}
