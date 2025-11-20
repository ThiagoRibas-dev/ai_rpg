from typing import Any, Optional
from app.tools.builtin._state_storage import get_entity, set_entity

def handler(
    from_key: str,
    to_key: str,
    direction: str,
    display_name: str,
    back_direction: Optional[str] = None,
    is_hidden: bool = False,
    is_locked: bool = False,
    one_way: bool = False,
    **context: Any
) -> dict:
    """
    Handler for location.connect. 
    Establishes edges between location nodes.
    """
    session_id = context["session_id"]
    db = context["db_manager"]

    # 1. Load Entities
    loc_from = get_entity(session_id, db, "location", from_key)
    loc_to = get_entity(session_id, db, "location", to_key)

    if not loc_from or not loc_to:
        return {"success": False, "error": f"One or both locations do not exist: '{from_key}', '{to_key}'."}

    # 2. Add Forward Connection
    # Structure: connections[direction] = { target_key, display_name, flags }
    loc_from.setdefault("connections", {})[direction] = {
        "target_key": to_key,
        "display_name": display_name,
        "is_hidden": is_hidden,
        "is_locked": is_locked
    }
    set_entity(session_id, db, "location", from_key, loc_from)

    # 3. Add Backward Connection (if not one-way)
    if not one_way:
        if not back_direction:
            # Try to infer opposite? No, better to error and force AI to be explicit.
            return {"success": False, "error": "back_direction is required for two-way connections."}
            
        loc_to.setdefault("connections", {})[back_direction] = {
            "target_key": from_key,
            "display_name": f"Back to {loc_from.get('name', 'Previous Area')}",
            "is_hidden": is_hidden, # Usually if one side is hidden, the other is too.
            "is_locked": is_locked
        }
        set_entity(session_id, db, "location", to_key, loc_to)

    return {
        "success": True, 
        "link": f"{from_key} ({direction}) -> {to_key}",
        "two_way": not one_way
    }
