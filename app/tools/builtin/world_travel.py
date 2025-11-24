import logging
from typing import Any
from app.tools.builtin._state_storage import get_entity, set_entity

logger = logging.getLogger(__name__)


def handler(destination: str, **context: Any) -> dict:
    """Moves party and simulates NPCs at destination."""
    session_id = context.get("session_id")
    db = context.get("db_manager")
    sim_service = context.get("simulation_service")
    current_time = context.get("current_game_time")

    if not session_id or not db:
        return {"status": "Error", "error": "Missing session context"}

    # --- 1. EXECUTE MOVE (Logic inlined from scene_move_to) ---
    scene = get_entity(session_id, db, "scene", "active_scene")
    if not scene:
        # Auto-create scene if missing
        scene = {"members": ["character:player"], "state_tags": []}

    current_loc_key = scene.get("location_key")
    new_location_key = destination
    move_success = True
    error_msg = None

    # Validation Logic
    if current_loc_key and current_loc_key != new_location_key:
        current_loc = get_entity(session_id, db, "location", current_loc_key)
        if current_loc:
            connections = current_loc.get("connections", {})
            # Check neighbors
            for direction, data in connections.items():
                if data["target_key"] == new_location_key:
                    if data.get("is_locked"):
                        move_success = False
                        error_msg = f"The exit '{direction}' is locked."
                    break

            # Strict movement check (Optional: disable for 'teleport' style travel if desired)
            # For ReAct, we usually allow it if the AI calls it, assuming AI checked logic.
            pass

    if not move_success:
        return {"status": "Failed to move", "error": error_msg}

    # Move Members
    members_to_move = scene.get("members", [])
    for member_id_str in members_to_move:
        try:
            entity_type, entity_key = member_id_str.split(":", 1)
            if entity_type == "character":
                char = get_entity(session_id, db, "character", entity_key)
                if char:
                    char["location_key"] = new_location_key
                    set_entity(session_id, db, "character", entity_key, char)
        except Exception as e:
            logger.warning(f"Could not move member '{member_id_str}': {e}")

    # Update Scene
    scene["location_key"] = new_location_key
    set_entity(session_id, db, "scene", "active_scene", scene)

    # Fetch visual desc for result
    loc_data = get_entity(session_id, db, "location", new_location_key)
    visuals = loc_data.get("description_visual", "") if loc_data else ""

    # --- 2. JIT TRIGGER (Simulate NPCs in the NEW location) ---
    sim_notes = []
    if sim_service:
        # Reload scene to be safe
        scene = get_entity(session_id, db, "scene", "active_scene")
        members = scene.get("members", [])

        for member in members:
            if "player" in member:
                continue
            key = member.split(":")[-1]

            profile_data = get_entity(session_id, db, "npc_profile", key)
            if not profile_data:
                continue

            from app.models.npc_profile import NpcProfile

            profile = NpcProfile(**profile_data)

            char_data = get_entity(session_id, db, "character", key)
            name = char_data.get("name", key)

            outcome = sim_service.simulate_npc_downtime(name, profile, current_time)
            if outcome and outcome.is_significant:
                sim_notes.append(f"{name} update: {outcome.outcome_summary}")
                profile.last_updated_time = current_time
                db.game_state.set_entity(
                    session_id, "npc_profile", key, profile.model_dump()
                )

    return {
        "status": f"Moved to {destination}",
        "visuals": visuals,
        "world_events": sim_notes,
        "ui_event": "location_change",  # Signal to GUI
        "location_data": loc_data,
    }
