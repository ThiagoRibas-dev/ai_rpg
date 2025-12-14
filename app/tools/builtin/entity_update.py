from typing import Any, Dict, Optional
import logging
from app.services.state_service import get_entity, set_entity
from app.utils.math_engine import recalculate_derived_stats
from app.services.invariant_validator import validate_entity, set_path, get_path
from app.models.vocabulary import GameVocabulary

logger = logging.getLogger(__name__)

# Standard categories to check when a flat key is provided (e.g. "str" -> "attributes.str")
SEARCH_CATEGORIES = [
    "attributes", 
    "resources", 
    "skills", 
    "features", 
    "progression", 
    "identity",
    "meta"
]

def resolve_target_path(entity: dict, key: str, vocabulary: Optional[GameVocabulary]) -> Optional[str]:
    """
    Resolve a key to a specific dot-path in the entity.
    1. If it's already a dot-path, return it.
    2. If it's a flat key, look for it in standard categories.
    3. If vocabulary is present, validate the resolved path.
    """
    resolved_path = key

    # If it's a flat key, try to find where it lives
    if "." not in key:
        found = False
        # 1. Check Root
        if key in entity:
            resolved_path = key
            found = True
        
        # 2. Check Categories
        if not found:
            for cat in SEARCH_CATEGORIES:
                if cat in entity and isinstance(entity[cat], dict) and key in entity[cat]:
                    resolved_path = f"{cat}.{key}"
                    found = True
                    break
        
        # 3. If still not found, defaults to root (will create new key) unless Vocab forbids it
        if not found:
            resolved_path = key

    # Validate against Vocabulary if available
    if vocabulary:
        # Check if path is valid
        if not vocabulary.validate_path(resolved_path):
            # Special case: The path might be valid but missing in the entity (creation)
            # We trust the vocabulary. If vocab says "attributes.str" is valid, we allow it.
            return resolved_path
            
            # If vocab says it's invalid (e.g. "attributes.stamina" when system uses "constitution"), reject.
            # However, we must allow standard fields not in vocab (like scene_state).
            # For now, we log warning but allow if it looks like a system field.
            # To be strict: return None if vocabulary.validate_path(resolved_path) is False
            pass

    return resolved_path

def handler(
    target_key: str,
    updates: Optional[Dict[str, Any]] = None,
    adjustments: Optional[Dict[str, int]] = None,
    inventory: Optional[Dict[str, Any]] = None,
    **context: Any,
) -> dict:
    session_id = context["session_id"]
    db = context["db_manager"]
    manifest = context.get("manifest", {})

    # 1. Load Entity
    etype = "character"
    if ":" in target_key:
        etype, target_key = target_key.split(":", 1)

    entity = get_entity(session_id, db, etype, target_key)
    if not entity:
        return {"error": f"Entity {etype}:{target_key} not found"}

    # 2. Load Vocabulary & Template
    vocabulary = None
    if manifest.get("vocabulary"):
        try:
            vocabulary = GameVocabulary(**manifest["vocabulary"])
        except Exception as e:
            logger.warning(f"Failed to load vocabulary for validation: {e}")

    tid = entity.get("template_id")
    template = db.stat_templates.get_by_id(tid) if tid else None

    changes_log = []
    errors = []

    # 3. Apply Adjustments (Relative Math)
    if adjustments:
        for key, delta in adjustments.items():
            path = resolve_target_path(entity, key, vocabulary)
            
            # If vocabulary exists and path is invalid, reject
            if vocabulary and not vocabulary.validate_path(path):
                # Allow non-vocab keys if they exist in entity (legacy/custom support)
                if get_path(entity, path) is None:
                    errors.append(f"Invalid path '{path}' for this system.")
                    continue

            current_val = get_path(entity, path)
            
            # Handle Pools (Dictionary with current/max)
            if isinstance(current_val, dict) and "current" in current_val:
                # Target the .current sub-path
                path = f"{path}.current"
                current_val = current_val["current"]
            
            if isinstance(current_val, (int, float)):
                new_val = current_val + delta
                set_path(entity, path, new_val)
                changes_log.append(f"{path}: {current_val} -> {new_val}")
            else:
                errors.append(f"Cannot adjust '{path}': value {current_val} is not a number.")

    # 4. Apply Updates (Absolute Set)
    if updates:
        for key, value in updates.items():
            path = resolve_target_path(entity, key, vocabulary)
            
            if vocabulary and not vocabulary.validate_path(path):
                 # Allow if it's a known non-vocab field (like location_key)
                 if path not in ["location_key", "disposition", "scene_state"]:
                     if get_path(entity, path) is None:
                        errors.append(f"Invalid path '{path}' rejected by system rules.")
                        continue

            # Handle Pools: if update value is int but target is pool, update .current
            current_val = get_path(entity, path)
            if isinstance(current_val, dict) and "current" in current_val and isinstance(value, (int, float)):
                path = f"{path}.current"
            
            set_path(entity, path, value)
            changes_log.append(f"Set {path} = {value}")

    # 5. Apply Inventory Changes
    if inventory:
        # Standardize storage: entity["inventory"]["backpack"] is the default list
        # We try to respect existing structure
        inv_cat = entity.get("inventory", {})
        if isinstance(inv_cat, list):
            # Legacy flat list
            target_list = inv_cat
        else:
            # Modern dict of lists
            if "backpack" not in inv_cat:
                inv_cat["backpack"] = []
            target_list = inv_cat["backpack"]
            entity["inventory"] = inv_cat # Ensure reassignment if it was None

        if "add" in inventory:
            item = inventory["add"]
            # Normalize to object
            item_obj = {"name": item, "qty": 1} if isinstance(item, str) else item
            target_list.append(item_obj)
            changes_log.append(f"Added item: {item_obj.get('name')}")
        
        if "remove" in inventory:
            item_name = inventory["remove"]
            # Find and remove
            for i, it in enumerate(target_list):
                if it.get("name") == item_name:
                    target_list.pop(i)
                    changes_log.append(f"Removed item: {item_name}")
                    break

    # 6. Recalculate Derived Stats
    if template:
        entity = recalculate_derived_stats(entity, template)

    # 7. Invariant Validation
    ruleset_id = manifest.get("ruleset_id")
    if ruleset_id:
        try:
            ruleset = db.rulesets.get_by_id(ruleset_id)
            if ruleset and ruleset.state_invariants:
                entity, fixes, warnings = validate_entity(
                    entity, ruleset.state_invariants, vocabulary, auto_correct=True
                )
                changes_log.extend([f"Fixed: {f}" for f in fixes])
                changes_log.extend([f"Warning: {w}" for w in warnings])
        except Exception as e:
            logger.warning(f"Invariant validation failed: {e}")

    # 8. Persist
    set_entity(session_id, db, etype, target_key, entity)

    return {
        "success": True, 
        "changes": changes_log, 
        "errors": errors if errors else None
    }
