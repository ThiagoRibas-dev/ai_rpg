from typing import Any, List, Dict
from app.tools.builtin._state_storage import set_entity, get_entity

_REVERSE_DIRS = {
    "north": "south", "south": "north",
    "east": "west", "west": "east",
    "northeast": "southwest", "southwest": "northeast",
    "northwest": "southeast", "southeast": "northwest",
    "up": "down", "down": "up",
    "in": "out", "out": "in",
    "enter": "exit", "exit": "enter",
    "ascend": "descend", "descend": "ascend"
}

def handler(
    key: str,
    name_display: str,
    description_visual: str,
    description_sensory: str,
    type: str,
    neighbors: List[Dict[str, str]] = None,
    **context: Any
) -> dict:
    """
    Handler for location.create.
    Initializes a location entity with the correct structure and an empty connections dict.
    Automatically handles bidirectional linking if neighbors are provided.
    """
    session_id = context["session_id"]
    db = context["db_manager"]

    # Check if updating existing or creating new
    existing = get_entity(session_id, db, "location", key)
    connections = existing.get("connections", {}) if existing else {}
    
    location_data = {
        "name": name_display,
        "description_visual": description_visual,
        "description_sensory": description_sensory,
        "type": type,
        "connections": connections 
    }

    # Process Neighbors
    if neighbors:
        for neighbor in neighbors:
            target_key = neighbor.get("target_key")
            direction = neighbor.get("direction", "unknown")
            
            if not target_key:
                continue

            # 1. Verify Target Exists
            target_loc = get_entity(session_id, db, "location", target_key)
            if not target_loc:
                # In batch generation (Wizard), target might not exist yet.
                # We allow the "Forward" link, assuming the target will be created shortly.
                # However, we cannot add the "Reverse" link to a non-existent entity.
                pass
            
            # 2. Add Forward Link (New -> Neighbor)
            location_data["connections"][direction] = {
                "target_key": target_key,
                "display_name": target_loc.get("name", target_key) if target_loc else target_key,
                "is_hidden": False,
                "is_locked": False
            }

            # 3. Add Reverse Link (Neighbor -> New)
            if target_loc:
                # Infer reverse direction
                rev_dir = _REVERSE_DIRS.get(direction.lower(), f"Back to {name_display}")
                
                target_loc.setdefault("connections", {})[rev_dir] = {
                    "target_key": key,
                    "display_name": name_display,
                    "is_hidden": False,
                    "is_locked": False
                }
                set_entity(session_id, db, "location", target_key, target_loc)

    version = set_entity(session_id, db, "location", key, location_data)

    return {
        "success": True,
        "key": key,
        "name": name_display,
        "version": version,
        "neighbors_linked": len(neighbors) if neighbors else 0
    }
