import re


def _parse_duration(description: str) -> int:
    description = description.lower()
    hours_match = re.search(r"(\d+)\s*hour", description)
    if hours_match:
        return int(hours_match.group(1))
    days_match = re.search(r"(\d+)\s*day", description)
    if days_match:
        return int(days_match.group(1)) * 24
    if "night" in description or "sleep" in description:
        return 8
    return 0


def handler(description: str, new_time: str, **context: dict) -> dict:
    """Advance time and trigger JIT simulation."""
    session_id = context.get("session_id")
    db = context.get("db_manager")
    sim_service = context.get("simulation_service")
    current_time = context.get("current_game_time")

    if not session_id or not db:
        raise ValueError("Missing session context")

    duration = _parse_duration(description)

    # --- JIT TRIGGER ---
    sim_results = []
    if sim_service and duration > 4:  # Only simulate if > 4 hours passed
        # Get all active NPCs (simple approximation: check scene members)
        # For a robust system, we might query all NPCs in the region, but for local models, keep it scoped.
        from app.services.state_service import get_entity

        scene = get_entity(session_id, db, "scene", "active_scene")
        members = scene.get("members", [])

        for member in members:
            if "player" in member:
                continue
            key = member.split(":")[-1]

            # Load profile
            profile_data = get_entity(session_id, db, "npc_profile", key)
            if not profile_data:
                continue

            # Check if stale? (Simplification: Just run it if time passed)
            from app.models.npc_profile import NpcProfile

            profile = NpcProfile(**profile_data)

            # Run Sim
            char_data = get_entity(session_id, db, "character", key)
            name = char_data.get("name", key)

            outcome = sim_service.simulate_npc_downtime(name, profile, new_time)
            if outcome and outcome.is_significant:
                sim_results.append(f"{name}: {outcome.outcome_summary}")
                # Save updated time
                profile.last_updated_time = new_time
                db.game_state.set_entity(
                    session_id, "npc_profile", key, profile.model_dump()
                )

    return {
        "old_time": current_time,
        "new_time": new_time,
        "description": description,
        "duration_hours": duration,
        "simulated_events": sim_results,
    }
