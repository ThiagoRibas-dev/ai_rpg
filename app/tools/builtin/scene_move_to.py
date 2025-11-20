# app/tools/builtin/scene_move_to.py
import logging
from typing import Any
from app.tools.builtin._state_storage import get_entity, set_entity

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
        
    # GRAPH VALIDATION LOGIC
    current_loc_key = scene.get("location_key")
    
    # If we are currently nowhere (setup/init), allow teleport.
    # Otherwise, check connections.
    if current_loc_key and current_loc_key != new_location_key:
        current_loc = get_entity(session_id, db, "location", current_loc_key)
        
        if current_loc:
            connections = current_loc.get("connections", {})
            valid_move = False
            
            # Check if requested target is a valid neighbor
            for direction, data in connections.items():
                if data["target_key"] == new_location_key:
                    if data.get("is_locked"):
                        return {"success": False, "error": f"The exit '{direction}' is locked."}
                    valid_move = True
                    break
            
            if not valid_move:
                return {"success": False, "error": f"No direct connection from '{current_loc_key}' to '{new_location_key}'. You must use 'location.connect' first if this is a new path."}

    members_to_move = scene.get("members", [])
    
    # 1. Update the location for each member individually
    for member_id_str in members_to_move:
        try:
            entity_type, entity_key = member_id_str.split(":", 1)
            if entity_type == "character":
                # Refactor: Direct update instead of patch
                char = get_entity(session_id, db, "character", entity_key)
                if char:
                    char["location_key"] = new_location_key
                    set_entity(session_id, db, "character", entity_key, char)
        except Exception as e:
            logger.warning(f"Could not move member '{member_id_str}': {e}")
    
    # 2. Update the scene's location
    scene["location_key"] = new_location_key
    set_entity(session_id, db, "scene", "active_scene", scene)

    # Return UI event for the frontend to render the Location Card
    return {
        "success": True, 
        "new_location": new_location_key, 
        "members_moved": len(members_to_move),
        "ui_event": "location_change", # Signal to GUI
        "location_data": get_entity(session_id, db, "location", new_location_key)
    }
