from typing import Any, Dict, Optional
from app.tools.builtin._state_storage import get_entity, set_entity

def handler(
    target_key: str,
    updates: Optional[Dict[str, Any]] = None,
    adjustments: Optional[Dict[str, int]] = None,
    inventory: Optional[Dict[str, Any]] = None,
    **context: Any
) -> dict:
    """
    Super-tool for updating entity state.
    - updates: Absolute sets (e.g. {"status": "Prone", "location": "jail"})
    - adjustments: Relative math on integers (e.g. {"hp": -5, "gold": +10})
    - inventory: Dict with 'add' or 'remove' keys (e.g. {"add": {"name": "Sword", "qty": 1}})
    """
    session_id = context["session_id"]
    db = context["db_manager"]

    # Resolve target (handle "player" shorthand)
    entity_type = "character" # Default
    if ":" in target_key:
        entity_type, target_key = target_key.split(":", 1)
    
    entity = get_entity(session_id, db, entity_type, target_key)
    if not entity:
        return {"success": False, "error": f"Entity {target_key} not found"}

    log = []

    # 1. Handle Relative Adjustments (Math)
    if adjustments:
        for key, delta in adjustments.items():
            # Check Vitals first (complex objects)
            vitals = entity.get("vitals", {})
            if key in vitals:
                # Handle {current, max} or scalar
                val_data = vitals[key]
                if isinstance(val_data, dict):
                    old_val = val_data.get("current", 0)
                    new_val = old_val + delta
                    # Clamp to max if exists
                    if "max" in val_data:
                        new_val = min(new_val, val_data["max"])
                    val_data["current"] = new_val
                    log.append(f"{key}: {old_val}->{new_val}")
                else:
                    # scalar fallback
                    new_val = int(val_data) + delta
                    vitals[key] = new_val
                    log.append(f"{key}: {val_data}->{new_val}")
            else:
                # Check Abilities/Root keys
                abilities = entity.get("abilities", {})
                if key in abilities:
                    old_val = abilities[key]
                    abilities[key] = old_val + delta
                    log.append(f"{key}: {old_val}->{abilities[key]}")

    # 2. Handle Absolute Updates
    if updates:
        for key, value in updates.items():
            # Simple root set for now
            entity[key] = value
            log.append(f"Set {key}={value}")

    # 3. Handle Inventory
    if inventory:
        slots = entity.setdefault("slots", {})
        default_slot = next(iter(slots)) if slots else "Inventory"
        target_list = slots.setdefault(default_slot, [])
        
        if "add" in inventory:
            item = inventory["add"] # {"name": "X", "qty": 1}
            target_list.append(item)
            log.append(f"Added {item.get('name')}")

    set_entity(session_id, db, entity_type, target_key, entity)

    return {"success": True, "target": target_key, "changes": log}
