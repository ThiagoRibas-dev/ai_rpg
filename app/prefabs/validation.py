"""
Entity Validation Pipeline
==========================
Centralized logic for enforcing SystemManifest rules on Entity state.

Pipeline Steps:
1.  **Context Build:** Flatten entity data for formula evaluation.
2.  **Aliases:** Compute system aliases (e.g., "str_mod").
3.  **Derived Stats:** Calculate fields with `formula` (e.g., AC, Initiative).
4.  **Dynamic Limits:** Calculate `max_formula` for pools (e.g., Max HP).
5.  **Prefab Constraints:** Enforce bounds (min/max) and shape (current <= max).

Usage:
    entity, changes = validate_entity(entity, manifest)
"""

import logging
from typing import Any, Dict, List, Tuple, Optional
import copy

from app.prefabs.manifest import SystemManifest
from app.prefabs.registry import PREFABS
from app.prefabs.formula import build_formula_context, evaluate, evaluate_int

logger = logging.getLogger(__name__)


# =============================================================================
# PATH UTILITIES
# =============================================================================

def get_path(data: Dict, path: str) -> Any:
    """Safely get nested dictionary value."""
    if not path:
        return None
    current = data
    try:
        for key in path.split("."):
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current
    except Exception:
        return None

def set_path(data: Dict, path: str, value: Any) -> bool:
    """Safely set nested dictionary value, creating path if needed."""
    if not path:
        return False
    keys = path.split(".")
    current = data
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
        if not isinstance(current, dict):
            return False # Path blocked by non-dict
    current[keys[-1]] = value
    return True

# =============================================================================
# MAIN PIPELINE
# =============================================================================

def validate_entity(
    entity: Dict[str, Any], 
    manifest: Optional[SystemManifest]
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Run the full validation pipeline on an entity.
    
    Args:
        entity: The entity state dictionary
        manifest: The system manifest (rules)
        
    Returns:
        (validated_entity, list_of_change_logs)
    """
    if not manifest:
        return entity, []

    # Work on a copy to avoid partial mutation state issues
    # (Though in tools we often want mutation; for safety we copy here)
    # Optimization: In a tight loop, we might skip deepcopy, but for RPG turns it's fine.
    validated = copy.deepcopy(entity)
    changes = []

    # --- PHASE 1: BUILD CONTEXT & RESOLVE ALIASES ---
    # We need a flat context for math (e.g. {"attributes_str": 18})
    # We also compute global aliases (e.g. {"str_mod": 4})
    context = build_formula_context(validated, aliases=manifest.aliases)

    # --- PHASE 2: COMPUTE DERIVED FIELDS (Formulas) ---
    # Fields that have a 'formula' are read-only derived values.
    # e.g. AC = 10 + dex_mod
    
    for field in manifest.fields:
        if field.formula:
            old_val = get_path(validated, field.path)
            
            # Evaluate formula
            # Note: We rely on the context having aliases from Phase 1
            new_val = evaluate(field.formula, context)
            
            # Type coercion based on prefab (mostly Ints for derived stats)
            if field.prefab.startswith("VAL_INT") or field.prefab == "RES_COUNTER":
                new_val = int(new_val)
            
            if old_val != new_val:
                set_path(validated, field.path, new_val)
                # Update context for subsequent dependencies
                context = build_formula_context(validated, aliases=manifest.aliases)
                # We don't log derived updates to avoid spam, or we log verbose?
                # changes.append(f"Derived {field.label}: {old_val} -> {new_val}")

    # --- PHASE 3: COMPUTE DYNAMIC LIMITS (Max Formulas) ---
    # Fields like HP often have a calculated Max.
    # e.g. HP Max = 10 + con_mod
    
    for field in manifest.fields:
        if field.prefab == "RES_POOL" and field.max_formula:
            pool = get_path(validated, field.path)
            if not isinstance(pool, dict):
                # Auto-repair bad shape
                pool = {"current": 0, "max": 0}
                set_path(validated, field.path, pool)
            
            old_max = pool.get("max", 0)
            new_max = evaluate_int(field.max_formula, context)
            
            if old_max != new_max:
                pool["max"] = new_max
                changes.append(f"Updated {field.label} Max: {old_max} -> {new_max}")
                # Note: We don't write back to 'validated' yet, 'pool' is a reference 
                # (if it was a dict in the original structure). 
                # To be safe with deepcopy/get_path:
                set_path(validated, field.path, pool)

    # --- PHASE 4: PREFAB VALIDATION (Clamping) ---
    # Enforce bounds (min/max), track lengths, pool integrity (cur <= max).
    
    for field in manifest.fields:
        prefab_def = PREFABS.get(field.prefab)
        if not prefab_def:
            continue

        current_val = get_path(validated, field.path)
        
        # If value is missing, insert default
        if current_val is None:
            default_val = prefab_def.get_default(field.config)
            set_path(validated, field.path, default_val)
            current_val = default_val
            # changes.append(f"Initialized {field.label}")

        # Run Prefab Validator
        # This handles: HP > Max -> Clamp;  Stat > 20 -> Clamp;
        corrected_val = prefab_def.validate(current_val, field.config)
        
        # Check for change
        if corrected_val != current_val:
            set_path(validated, field.path, corrected_val)
            
            # Format nice log message
            msg = f"{field.label}: "
            if field.prefab == "RES_POOL":
                msg += f"{current_val.get('current')} -> {corrected_val.get('current')}"
            else:
                msg += f"{current_val} -> {corrected_val}"
            
            changes.append(msg)

    return validated, changes
