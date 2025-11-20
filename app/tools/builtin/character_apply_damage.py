from typing import Any
from app.tools.builtin._state_storage import get_entity, set_entity

def handler(
    target_key: str,
    amount: int,
    explanation: str,
    vital_name: str = "HP",
    damage_type: str = "physical",
    **context: Any
) -> dict:
    """
    Handler for character.apply_damage.
    Reduces vital current value and applies status effects if zero.
    """
    session_id = context["session_id"]
    db = context["db_manager"]

    entity = get_entity(session_id, db, "character", target_key)
    if not entity:
        return {"success": False, "error": f"Character '{target_key}' not found."}

    # Navigate complex vital structure: vitals -> HP -> {current, max}
    vitals = entity.get("vitals", {})
    target_vital = vitals.get(vital_name)

    # Handle both scalar (simple int) and dict {current, max} formats for robustness
    current_val = 0
    if isinstance(target_vital, dict):
        current_val = target_vital.get("current", 0)
    elif isinstance(target_vital, (int, float)):
        current_val = int(target_vital)
        # Upgrade to dict structure to be safe
        vitals[vital_name] = {"current": current_val, "max": current_val} # Assume max=current if generic
        target_vital = vitals[vital_name]
    else:
        # Initialize if missing
        current_val = 10 # Fallback
        vitals[vital_name] = {"current": 10, "max": 10}
        target_vital = vitals[vital_name]

    # Apply Math
    new_val = current_val - amount
    
    # Update Entity
    if isinstance(target_vital, dict):
        target_vital["current"] = new_val
    else:
        # Should not happen due to upgrade block above, but safety first
        vitals[vital_name] = new_val

    # Status Check
    status_update = "Alive"
    condition_applied = None
    
    if new_val <= 0:
        status_update = "Critical/Unconscious"
        condition_applied = "Unconscious"
        # Auto-add condition if structure exists
        if "conditions" not in entity:
            entity["conditions"] = []
        if condition_applied not in entity["conditions"]:
            entity["conditions"].append(condition_applied)

    # Save
    set_entity(session_id, db, "character", target_key, entity)

    return {
        "success": True,
        "target": target_key,
        "damage_amount": amount,
        "vital": vital_name,
        "previous_value": current_val,
        "new_value": new_val,
        "status": status_update,
        "condition_applied": condition_applied,
        "narrative_cue": explanation
    }
