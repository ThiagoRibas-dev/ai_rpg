import logging
from typing import Dict, Any
from simpleeval import simple_eval, NameNotDefined
from app.models.stat_block import StatBlockTemplate

logger = logging.getLogger(__name__)

def safe_evaluate(expression: str, context: Dict[str, Any]) -> int | float:
    """
    Safely evaluate a mathematical expression using simpleeval.
    Returns 0 if evaluation fails.
    """
    try:
        # Ensure all context values are numbers (handle None or strings)
        safe_context = {}
        for k, v in context.items():
            try:
                safe_context[k] = float(v)
            except (ValueError, TypeError):
                safe_context[k] = 0

        return simple_eval(expression, names=safe_context)
    except (NameNotDefined, SyntaxError, Exception) as e:
        logger.warning(f"Math evaluation failed for '{expression}': {e}")
        return 0

def recalculate_derived_stats(entity_data: Dict[str, Any], stat_template: StatBlockTemplate) -> Dict[str, Any]:
    """
    Recalculates Derived Stats and Vital Max values based on Abilities.
    Updates the entity_data dictionary in place and returns it.
    """
    if not entity_data or not stat_template:
        return entity_data

    # 1. Build Context from Abilities
    # Flatten {abilities: {STR: 10}} -> {STR: 10} for easy formula access
    math_context = {}
    abilities = entity_data.get("abilities", {})
    
    # Add raw abilities
    for name, value in abilities.items():
        math_context[name] = value
        # Also add common shorthand if not present (e.g. Strength -> STR)
        # This logic relies on the template defs if we wanted to be robust, 
        # but for now we trust the keys match the template names.
        
        # Auto-calculate Modifiers for d20 systems if values are integers
        # e.g. If STR is 18, define STR_mod = 4
        if isinstance(value, int):
            mod = (value - 10) // 2
            math_context[f"{name}_mod"] = mod
            math_context[f"{name}Mod"] = mod

    # Add current level if available
    math_context["Level"] = entity_data.get("level", 1)
    math_context["PB"] = 2 + ((math_context["Level"] - 1) // 4) # D&D Proficiency Bonus approximation

    # 2. Calculate Derived Stats
    if stat_template.derived_stats:
        entity_data.setdefault("derived", {})
        for derived_def in stat_template.derived_stats:
            if derived_def.formula:
                val = safe_evaluate(derived_def.formula, math_context)
                # Round to nearest int usually desirable for stats
                entity_data["derived"][derived_def.name] = int(val)
                
                # Add derived stats to context so subsequent formulas can use them
                math_context[derived_def.name] = int(val)

    # 3. Calculate Vital Maxima
    if stat_template.vitals:
        entity_data.setdefault("vitals", {})
        for vital_def in stat_template.vitals:
            if vital_def.max_formula:
                max_val = safe_evaluate(vital_def.max_formula, math_context)
                max_val = max(vital_def.min_value, int(max_val))
                
                # Update max in the complex vital object
                current_vital_data = entity_data["vitals"].get(vital_def.name, {})
                
                # Handle format variants (scalar vs dict)
                if isinstance(current_vital_data, dict):
                    current_vital_data["max"] = max_val
                    # Clamp current if it exceeds new max? Optional, but good practice.
                    if "current" in current_vital_data:
                        current_vital_data["current"] = min(current_vital_data["current"], max_val)
                    else:
                        current_vital_data["current"] = max_val
                else:
                    # Upgrade scalar to dict
                    current_vital_data = {"current": current_vital_data if isinstance(current_vital_data, int) else max_val, "max": max_val}
                
                entity_data["vitals"][vital_def.name] = current_vital_data

    return entity_data
