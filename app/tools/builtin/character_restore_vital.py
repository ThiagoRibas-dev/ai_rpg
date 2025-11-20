from typing import Any
from app.tools.builtin._state_storage import get_entity, set_entity

def handler(
    target_key: str,
    amount: int,
    vital_name: str = "HP",
    **context: Any
) -> dict:
    """
    Handler for character.restore_vital.
    Increases vital value, clamping to Max.
    """
    session_id = context["session_id"]
    db = context["db_manager"]

    entity = get_entity(session_id, db, "character", target_key)
    if not entity:
        return {"success": False, "error": f"Character '{target_key}' not found."}

    vitals = entity.get("vitals", {})
    target_vital = vitals.get(vital_name)

    if not target_vital:
        return {"success": False, "error": f"Vital '{vital_name}' not found on character."}

    current_val = 0
    max_val = 999 # Fallback
    
    if isinstance(target_vital, dict):
        current_val = target_vital.get("current", 0)
        max_val = target_vital.get("max", current_val)
    elif isinstance(target_vital, (int, float)):
        current_val = int(target_vital)
        max_val = current_val # If simple scalar, max is effectively current? Or undefined.
    
    # Math
    new_val = min(current_val + amount, max_val)
    
    # Update
    if isinstance(target_vital, dict):
        target_vital["current"] = new_val
    else:
        vitals[vital_name] = new_val
        
    set_entity(session_id, db, "character", target_key, entity)

    return {
        "success": True,
        "target": target_key,
        "healed_amount": amount,
        "vital": vital_name,
        "new_value": new_val,
        "max_value": max_val,
        "is_full": new_val >= max_val
    }
