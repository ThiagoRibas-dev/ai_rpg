from typing import Any, Dict, Optional
from app.services.state_service import get_entity, set_entity


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

    # --- Load Template for Validation & Mapping ---
    tid = entity.get("template_id")
    template = None
    if tid:
        template = db.stat_templates.get_by_id(tid)

    changes_log = []

    # Helper function to sanitize inputs based on template
    def sanitize_value(key: str, val: Any) -> Any:
        if not template:
            return val

        # Check if this key exists in fundamentals or derived
        stat_def = template.fundamentals.get(key) or template.derived.get(key)

        if stat_def:
            # 1. Handle Enum/Ladder Reverse Lookup
            # If input is string but we expect int, check lookup map
            if isinstance(val, str):
                # Check for explicit lookup map
                # The schema definition for StatRendering needs to be accessed
                # We assume stat_def has a 'rendering' field or similar metadata if defined in schema
                # Based on your StatBlockTemplate, 'rendering' is usually on Tracks,
                # but let's assume we might add it to StatValue or use the 'widget' type.

                # Check if it's a Ladder widget or has lookup map in metadata
                # Note: In your current schema, StatValue doesn't explicitly hold 'rendering' dict,
                # but usually Ladder logic implies a map exists.
                # If you extended StatValue to have 'rendering', you'd check it here.

                # Simple Heuristic: If we can't cast to float/int, but we need to.
                if (
                    stat_def.data_type in ["integer", "float"]
                    and not val.replace("-", "").isdigit()
                ):
                    # Attempt to find it in a hypothetical lookup (if you stored it)
                    # For now, let's just try to be robust against strings like "Good (+3)"
                    # Regex to extract number from "Good (+3)"
                    import re

                    match = re.search(r"([+-]?\d+)", val)
                    if match:
                        return int(match.group(1))

        return val

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
            # Sanitize Value (Handle "Good (+3)" -> 3)
            clean_v = sanitize_value(k, v)

            if k in entity.get("fundamentals", {}):
                entity["fundamentals"][k] = clean_v
            elif k in entity.get("derived", {}):
                entity["derived"][k] = clean_v
            elif k in entity.get("gauges", {}):
                # Handle direct int set vs dict set
                if isinstance(clean_v, (int, float)):
                    entity["gauges"][k]["current"] = clean_v
                elif isinstance(clean_v, dict):
                    entity["gauges"][k].update(clean_v)
            else:
                # Fallback to root (e.g. name, location_key)
                entity[k] = clean_v

            changes_log.append(f"Set {k} = {clean_v}")

    # 3. Inventory (Add only for now)
    if inventory and "add" in inventory:
        item = inventory["add"]  # This might be a Dict or a String depending on LLM

        # Normalize item
        if isinstance(item, str):
            item_obj = {"name": item, "qty": 1}
        else:
            item_obj = item  # Assuming dict

        # Default collection: find first available or make 'inventory'
        col_map = entity.setdefault("collections", {})
        col_key = "inventory"
        if "inventory" not in col_map and col_map:
            col_key = next(iter(col_map))

        target_list = col_map.setdefault(col_key, [])
        target_list.append(item_obj)
        changes_log.append(f"Added {item_obj.get('name')} to {col_key}")

    set_entity(session_id, db, etype, target_key, entity)
    return {"success": True, "changes": changes_log}
