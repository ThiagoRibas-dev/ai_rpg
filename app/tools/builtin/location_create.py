from typing import Any, Dict
from app.services.state_service import set_entity, get_entity

_REVERSE_DIRS = {
    "north": "south",
    "south": "north",
    "east": "west",
    "west": "east",
    "northeast": "southwest",
    "southwest": "northeast",
    "northwest": "southeast",
    "southeast": "northwest",
    "up": "down",
    "down": "up",
    "in": "out",
    "out": "in",
    "enter": "exit",
    "exit": "enter",
    "ascend": "descend",
    "descend": "ascend",
}


def handler(
    key: str,
    name_display: str,
    description_visual: str,
    description_sensory: str,
    type: str,
    neighbors: Dict[str, str] = None,
    **context: Any,
) -> dict:
    session_id = context["session_id"]
    db = context["db_manager"]

    existing = get_entity(session_id, db, "location", key)
    connections = existing.get("connections", {}) if existing else {}

    location_data = {
        "name": name_display,
        "description_visual": description_visual,
        "description_sensory": description_sensory,
        "type": type,
        "connections": connections,
    }

    linked_count = 0
    if neighbors:
        for direction, target_key in neighbors.items():
            if not target_key:
                continue

            # 1. Forward Link
            target_loc = get_entity(session_id, db, "location", target_key)
            target_name = (
                target_loc.get("name", target_key) if target_loc else target_key
            )

            location_data["connections"][direction] = {
                "target_key": target_key,
                "display_name": target_name,
                "is_hidden": False,
                "is_locked": False,
            }
            linked_count += 1

            # 2. Reverse Link
            if target_loc:
                rev_dir = _REVERSE_DIRS.get(
                    direction.lower(), f"Back to {name_display}"
                )
                target_loc.setdefault("connections", {})[rev_dir] = {
                    "target_key": key,
                    "display_name": name_display,
                    "is_hidden": False,
                    "is_locked": False,
                }
                set_entity(session_id, db, "location", target_key, target_loc)

    version = set_entity(session_id, db, "location", key, location_data)

    return {
        "success": True,
        "key": key,
        "name": name_display,
        "neighbors_linked": linked_count,
        "version": version,
    }
