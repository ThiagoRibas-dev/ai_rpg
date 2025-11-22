import logging
from typing import Dict, Any
from app.tools.builtin._state_storage import get_entity, set_entity

logger = logging.getLogger(__name__)

def handler(zones: list[Dict[str, Any]], layout_type: str = "grid", **context) -> Dict[str, Any]:
    """
    Handles the scene.define_zones tool call.
    Updates the active scene with new zone definitions.
    """
    session_id = context.get("session_id")
    db_manager = context.get("db_manager")

    if not session_id or not db_manager:
        return {"error": "Missing session context"}

    try:
        active_scene = get_entity(session_id, db_manager, "scene", "active_scene")
        if not active_scene:
            return {"error": "No active scene found for this session."}

        active_scene["zones"] = zones
        if layout_type:
            active_scene["layout_type"] = layout_type
        
        set_entity(session_id, db_manager, "scene", "active_scene", active_scene)
        logger.info(f"Defined zones for scene {session_id}: {zones}")
        
        # Trigger UI refresh for the scene map
        if context.get("ui_queue"):
            context["ui_queue"].put({"type": "turn_complete"}) 

        return {"success": True, "message": f"Scene zones updated. Layout type: {layout_type}"}

    except Exception as e:
        logger.error(f"Error defining zones for scene {session_id}: {e}", exc_info=True)
        return {"error": str(e)}
