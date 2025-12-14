from typing import Any, Dict, Optional
from app.services.state_service import get_entity, set_entity
from app.utils.math_engine import recalculate_derived_stats
from app.services.invariant_validator import validate_character


def deep_update(data: dict, key: str, value: Any) -> bool:
    """
    Recursively searches for 'key' in 'data'.
    If found, updates it and returns True.
    Prioritizes shallow matches.
    """
    # 1. Direct match
    if key in data:
        # Smart handling for pools (if updating a dict with a number, assume current)
        if (
            isinstance(data[key], dict)
            and "current" in data[key]
            and isinstance(value, (int, float))
        ):
            data[key]["current"] = value
        else:
            data[key] = value
        return True

    # 2. Recursive search
    for k, v in data.items():
        if isinstance(v, dict):
            if deep_update(v, key, value):
                return True

    return False


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
            # Use deep search to find the value to adjust
            # Note: deep_update is for SETTING, we need a finder for GETTING to adjust
            # For simplicity, we stick to the existing shallow logic for adjustments
            # OR we implement a deep_get. Given adjustments are usually stats (shallow),
            # we keep the shallow search for safety/speed for now, but extend to standard cats.

            found = False
            for cat in ["attributes", "resources", "skills"]:
                if cat in entity and k in entity[cat]:
                    old = entity[cat][k]
                    if isinstance(old, (int, float)):
                        entity[cat][k] += delta
                        changes_log.append(f"{k}: {old} -> {entity[cat][k]}")
                        found = True
                        break
                    elif isinstance(old, dict) and "current" in old:
                        cur = old["current"]
                        mx = old.get("max", 9999)
                        entity[cat][k]["current"] = max(0, min(cur + delta, mx))
                        changes_log.append(f"{k}: {cur} -> {entity[cat][k]['current']}")
                        found = True
                        break

            if not found:
                # Fallback for root
                if k in entity and isinstance(entity[k], (int, float)):
                    entity[k] += delta
                    changes_log.append(f"{k} adjusted by {delta}")

    # 2. Updates (Absolute Set - Intelligent)
    if updates:
        for k, v in updates.items():
            # Try Deep Search first
            found = deep_update(entity, k, v)

            if found:
                changes_log.append(f"Updated {k} -> {v}")
            else:
                # Check for dotted path (e.g. "inventory.bag.torch")
                if "." in k:
                    parts = k.split(".")
                    ref = entity
                    path_valid = True
                    for part in parts[:-1]:
                        if isinstance(ref, dict) and part in ref:
                            ref = ref[part]
                        else:
                            path_valid = False
                            break

                    if path_valid and isinstance(ref, dict):
                        ref[parts[-1]] = v
                        changes_log.append(f"Updated path {k} -> {v}")
                        found = True

            if not found:
                # Create new property at root
                entity[k] = v
                changes_log.append(f"Created {k} = {v}")

    # 3. Inventory (Add Item Wrapper)
    if inventory and "add" in inventory:
        item = inventory["add"]
        if isinstance(item, str):
            item_obj = {"name": item, "qty": 1}
        else:
            item_obj = item

        # Add to first available list or 'inventory' root
        col_map = entity.setdefault("inventory", {})
        if isinstance(col_map, list):  # Legacy
            col_map.append(item_obj)
        elif isinstance(col_map, dict):
            target = next(iter(col_map.values())) if col_map else []
            if isinstance(target, list):
                target.append(item_obj)
            else:
                # Create default backpack if empty
                entity["inventory"]["backpack"] = [item_obj]

        changes_log.append(f"Added {item_obj.get('name')}")

    # 4. Recalculate
    if template:
        entity = recalculate_derived_stats(entity, template)

    # === STATE INVARIANT VALIDATION ===
    # Apply game-system-specific constraints extracted from ruleset
    manifest = context.get("manifest", {})
    ruleset_id = manifest.get("ruleset_id")
    
    if ruleset_id:
        try:
            ruleset = db.rulesets.get_by_id(ruleset_id)
            if ruleset and hasattr(ruleset, 'state_invariants') and ruleset.state_invariants:
                entity, auto_fixes, warnings = validate_character(entity, ruleset)
                
                for fix in auto_fixes:
                    changes_log.append(f"🔧 Auto-corrected: {fix}")
                
                for warn in warnings:
                    changes_log.append(f"⚠️ {warn}")
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Invariant validation failed: {e}")



    # === VOCABULARY-AWARE INVARIANT VALIDATION ===
    manifest = context.get("manifest", {})
    ruleset_id = manifest.get("ruleset_id")
    
    if ruleset_id:
        try:
            ruleset = db.rulesets.get_by_id(ruleset_id)
            if ruleset:
                invariants = getattr(ruleset, 'state_invariants', [])
                
                if invariants:
                    from app.services.invariant_validator import validate_entity
                    
                    # Try to get vocabulary if available
                    vocabulary = None
                    vocab_data = manifest.get("vocabulary")
                    if vocab_data:
                        try:
                            from app.models.vocabulary import GameVocabulary
                            vocabulary = GameVocabulary(**vocab_data) if isinstance(vocab_data, dict) else None
                        except Exception:
                            pass
                    
                    entity, auto_fixes, warnings = validate_entity(
                        entity, invariants, vocabulary
                    )
                    
                    for fix in auto_fixes:
                        changes_log.append(f"🔧 {fix}")
                    
                    for warn in warnings:
                        changes_log.append(f"⚠️ {warn}")
                        
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Invariant validation failed: {e}")

    set_entity(session_id, db, etype, target_key, entity)
    return {"success": True, "changes": changes_log}
