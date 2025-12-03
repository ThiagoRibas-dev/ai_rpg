from typing import Any, Dict, Optional
from app.services.state_service import get_entity, set_entity
from app.utils.math_engine import recalculate_derived_stats

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

    tid = entity.get("template_id")
    template = db.stat_templates.get_by_id(tid) if tid else None
    
    changes_log = []

    # 1. Adjustments (Relative Math)
    if adjustments:
        for k, delta in adjustments.items():
            # Search in common categories
            found = False
            for cat in ["attributes", "resources", "skills"]:
                if cat in entity and k in entity[cat]:
                    # Atom
                    old = entity[cat][k]
                    if isinstance(old, (int, float)):
                        entity[cat][k] += delta
                        changes_log.append(f"{k}: {old} -> {entity[cat][k]}")
                        found = True
                        break
                    # Pool (Molecule)
                    elif isinstance(old, dict) and "current" in old:
                        cur = old["current"]
                        mx = old.get("max", 9999)
                        entity[cat][k]["current"] = max(0, min(cur + delta, mx))
                        changes_log.append(f"{k}: {cur} -> {entity[cat][k]['current']}")
                        found = True
                        break
            
            if not found:
                # Fallback for root keys
                if k in entity and isinstance(entity[k], (int, float)):
                     entity[k] += delta
                     changes_log.append(f"{k} adjusted by {delta}")

    # 2. Updates (Absolute Set)
    if updates:
        for k, v in updates.items():
            # Deep search for the key in categories to update it in place
            found = False
            for cat in ["attributes", "resources", "skills", "identity", "narrative"]:
                if cat in entity and k in entity[cat]:
                    # If target is a pool and we receive a number, assume Current
                    if isinstance(entity[cat][k], dict) and "current" in entity[cat][k] and isinstance(v, (int, float)):
                        entity[cat][k]["current"] = v
                    else:
                        entity[cat][k] = v
                    found = True
                    break
            
            if not found:
                # Set at root or create in 'attributes' as fallback?
                # Safer to just log error or set at root if generic
                entity[k] = v
            
            changes_log.append(f"Set {k} = {v}")

    # 3. Recalculate Logic
    if template:
        entity = recalculate_derived_stats(entity, template)

    set_entity(session_id, db, etype, target_key, entity)
    return {"success": True, "changes": changes_log}
