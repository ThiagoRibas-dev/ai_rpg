from typing import Any, Dict, Optional
from app.tools.builtin._state_storage import get_entity, set_entity


def handler(
    target_key: str,
    updates: Optional[Dict[str, Any]] = None,
    adjustments: Optional[Dict[str, int]] = None,
    inventory: Optional[Dict[str, Any]] = None,
    **context: Any,
) -> dict:
    session_id = context["session_id"]
    db = context["db_manager"]

    # Handle "player" alias
    etype = "character"
    if ":" in target_key:
        etype, target_key = target_key.split(":", 1)

    entity = get_entity(session_id, db, etype, target_key)
    if not entity:
        return {"error": "Entity not found"}

    changes_log = []

    # 1. Adjustments (Relative Math)
    if adjustments:
        for k, delta in adjustments.items():
            # Check Fundamentals
            if k in entity.get("fundamentals", {}):
                old = entity["fundamentals"][k]
                entity["fundamentals"][k] += delta
                changes_log.append(f"{k}: {old} -> {entity['fundamentals'][k]}")

            # Check Derived (Manual Override)
            elif k in entity.get("derived", {}):
                old = entity["derived"][k]
                entity["derived"][k] += delta
                changes_log.append(f"{k}: {old} -> {entity['derived'][k]}")

            # Check Gauges
            elif k in entity.get("gauges", {}):
                g = entity["gauges"][k]
                old = g["current"]
                # Clamp between 0 and Max
                mx = g.get("max", 9999)
                g["current"] = max(0, min(g["current"] + delta, mx))
                changes_log.append(f"{k}: {old} -> {g['current']}")

    # 2. Updates (Absolute Set)
    if updates:
        for k, v in updates.items():
            if k in entity.get("fundamentals", {}):
                entity["fundamentals"][k] = v
            elif k in entity.get("derived", {}):
                entity["derived"][k] = v
            elif k in entity.get("gauges", {}):
                # Handle direct int set vs dict set
                if isinstance(v, (int, float)):
                    entity["gauges"][k]["current"] = v
                elif isinstance(v, dict):
                    entity["gauges"][k].update(v)
            else:
                # Fallback to root (e.g. name, location_key)
                entity[k] = v
            changes_log.append(f"Set {k} = {v}")

    # 3. Inventory (Add only for now)
    if inventory and "add" in inventory:
        item = inventory["add"]
        # Default collection: find first available or make 'inventory'
        col_map = entity.setdefault("collections", {})
        col_key = "inventory"
        if "inventory" not in col_map and col_map:
            col_key = next(iter(col_map))

        target_list = col_map.setdefault(col_key, [])
        target_list.append(item)
        changes_log.append(f"Added {item.get('name')} to {col_key}")

    set_entity(session_id, db, etype, target_key, entity)
    return {"success": True, "changes": changes_log}
