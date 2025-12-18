
import logging
from typing import Any
from app.services.state_service import get_entity, set_entity

logger = logging.getLogger(__name__)

def handler(destination: str, **context: Any) -> dict:
    """
    Handler for 'move' tool.
    Updates active scene and player location.
    """
    session_id = context.get("session_id")
    db = context.get("db_manager")
    
    if not session_id or not db:
        return {"error": "Missing session context"}

    # 1. Get Scene
    scene = get_entity(session_id, db, "scene", "active_scene")
    if not scene:
        scene = {"members": ["character:player"], "location_key": "unknown"}

    current_loc = scene.get("location_key")
    
    # 2. Update Scene
    scene["location_key"] = destination
    set_entity(session_id, db, "scene", "active_scene", scene)

    # 3. Update Player Entity (Consistency)
    player = get_entity(session_id, db, "character", "player")
    if player:
        player["location_key"] = destination
        set_entity(session_id, db, "character", "player", player)

    # 4. Get Destination Details for Context
    loc_data = get_entity(session_id, db, "location", destination)
    loc_name = loc_data.get("name", destination) if loc_data else destination
    
    return {
        "status": "moved",
        "from": current_loc,
        "to": destination,
        "location_name": loc_name,
        "ui_event": "location_change", # Triggers UI refresh
        "location_data": loc_data
    }
