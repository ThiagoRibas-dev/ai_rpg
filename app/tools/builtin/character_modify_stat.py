from typing import Any
from app.tools.builtin._state_storage import get_entity, set_entity

def handler(
    target_key: str,
    stat_name: str,
    amount: int,
    duration: str,
    **context: Any
) -> dict:
    """
    Handler for character.modify_stat.
    Updates an ability score directly (simplified for now, ideally adds a 'modifier' object).
    """
    session_id = context["session_id"]
    db = context["db_manager"]

    entity = get_entity(session_id, db, "character", target_key)
    if not entity:
        return {"success": False, "error": f"Character '{target_key}' not found."}

    abilities = entity.get("abilities", {})
    
    # Simple integer modification
    # In a complex system, we would add a modifier object to a list to track duration.
    # For v2.0 MVP, we stick to direct value modification but log it.
    
    current_val = abilities.get(stat_name)
    if current_val is None:
         # Try searching case-insensitive
         for k in abilities.keys():
             if k.lower() == stat_name.lower():
                 stat_name = k
                 current_val = abilities[k]
                 break
    
    if current_val is None:
         return {"success": False, "error": f"Stat '{stat_name}' not found on character."}

    if not isinstance(current_val, int):
         return {"success": False, "error": f"Stat '{stat_name}' is not an integer, cannot modify math."}

    new_val = current_val + amount
    abilities[stat_name] = new_val
    
    set_entity(session_id, db, "character", target_key, entity)

    return {
        "success": True,
        "target": target_key,
        "stat": stat_name,
        "change": amount,
        "new_value": new_val,
        "duration": duration
    }
