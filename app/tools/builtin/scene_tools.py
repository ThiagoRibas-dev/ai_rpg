from typing import Dict, Any, List, Optional
from app.tools.registry import register_tool
from app.tools.schemas import SceneDefineZones, SceneMoveActor
from app.core.simulation_service import SimulationService
from app.tools.builtin._state_storage import get_entity, set_entity
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# Helper Functions
# =============================================================================


def _get_simulation_service(session_id: int) -> SimulationService:
    """Retrieves the simulation service for the given session."""
    # This is a placeholder. In a real app, you'd likely have a way to
    # access the SimulationService instance, perhaps from the orchestrator.
    # For now, we'll assume it's globally accessible or can be created.
    # This might need to be passed down through the tool execution context.
    # For now, we'll make a simplifying assumption.
    logger.warning("Accessing SimulationService in scene_tools is a placeholder. Refactor needed.")
    from main import orchestrator # Avoid circular import if possible
    return orchestrator.simulation_service


# =============================================================================
# Tool Handlers
# =============================================================================


@register_tool
def handle_scene_define_zones(tool: SceneDefineZones, session_id: int, db_manager) -> Dict[str, Any]:
    """
    Handles the scene.define_zones tool call.
    Updates the active scene with new zone definitions.
    """
    try:
        active_scene = get_entity(session_id, db_manager, "scene", "active_scene")
        if not active_scene:
            return {"error": "No active scene found for this session."}

        active_scene["zones"] = tool.zones
        if tool.layout_type:
            active_scene["layout_type"] = tool.layout_type
        
        set_entity(session_id, db_manager, "scene", "active_scene", active_scene)
        logger.info(f"Defined zones for scene {session_id}: {tool.zones}")
        return {"success": True, "message": f"Scene zones updated. Layout type: {tool.layout_type}"}

    except Exception as e:
        logger.error(f"Error defining zones for scene {session_id}: {e}", exc_info=True)
        return {"error": str(e)}


@register_tool
def handle_scene_move_actor(tool: SceneMoveActor, session_id: int, db_manager) -> Dict[str, Any]:
    """
    Handles the scene.move_actor tool call.
    Moves a character to a specified zone within the active scene.
    """
    try:
        character = get_entity(session_id, db_manager, "character", tool.actor_key)
        if not character:
            return {"error": f"Character '{tool.actor_key}' not found."}

        # Verify target_zone_id exists in active_scene's zones
        active_scene = get_entity(session_id, db_manager, "scene", "active_scene")
        if not active_scene:
            return {"error": "No active scene found. Cannot move actor."}
        
        zone_ids = [z["id"] for z in active_scene.get("zones", [])]
        if tool.target_zone_id not in zone_ids:
            return {"error": f"Target zone '{tool.target_zone_id}' not found in active scene zones."}

        # Update character's scene_state
        if "scene_state" not in character:
            character["scene_state"] = {}
        character["scene_state"]["zone_id"] = tool.target_zone_id
        character["scene_state"]["is_hidden"] = tool.is_hidden
        
        set_entity(session_id, db_manager, "character", tool.actor_key, character)
        logger.info(f"Moved actor '{tool.actor_key}' to zone '{tool.target_zone_id}' (hidden: {tool.is_hidden}).")
        return {"success": True, "message": f"Actor '{tool.actor_key}' moved to zone '{tool.target_zone_id}'."}

    except Exception as e:
        logger.error(f"Error moving actor '{tool.actor_key}' in scene {session_id}: {e}", exc_info=True)
        return {"error": str(e)}
