import logging
from typing import Dict, Any
from simpleeval import simple_eval
from app.models.stat_block import StatBlockTemplate

logger = logging.getLogger(__name__)

def safe_evaluate(expression: str, context: Dict[str, Any]) -> int | float:
    """Safely evaluate math expression."""
    if not expression or expression == "0" or expression == "null":
        return 0
    try:
        safe_context = {}
        for k, v in context.items():
            try:
                safe_context[k] = float(v)
            except (ValueError, TypeError):
                safe_context[k] = 0
        return simple_eval(expression, names=safe_context)
    except Exception as e:
        logger.warning(f"Math error '{expression}': {e}")
        return 0

def recalculate_derived_stats(entity_data: Dict[str, Any], stat_template: StatBlockTemplate) -> Dict[str, Any]:
    """Recalculates DerivedStats and Meter Maxima."""
    if not entity_data or not stat_template:
        return entity_data

    # 1. Build Context from Fundamental Stats
    math_context = {}
    fund = entity_data.get("fundamental_stats", {})
    
    for name, value in fund.items():
        math_context[name] = value
        if isinstance(value, int) and value >= 1:
            mod = (value - 10) // 2
            math_context[f"{name}_Mod"] = mod

    math_context["Level"] = entity_data.get("level", 1)

    # 2. Calculate Derived
    if stat_template.derived_stats:
        entity_data.setdefault("derived_stats", {})
        for calc_def in stat_template.derived_stats:
            if calc_def.formula:
                val = safe_evaluate(calc_def.formula, math_context)
                entity_data["derived_stats"][calc_def.name] = int(val)
                math_context[calc_def.name] = int(val)

    # 3. Calculate Vitals Max
    if stat_template.vital_resources:
        entity_data.setdefault("vital_resources", {})
        for v_def in stat_template.vital_resources:
            if v_def.max_formula:
                max_val = safe_evaluate(v_def.max_formula, math_context)
                max_val = max(v_def.min_value, int(max_val))
                
                curr_data = entity_data["vital_resources"].get(v_def.name, {})
                if not curr_data:
                    curr_data = {"current": max_val, "max": max_val}
                else:
                    curr_data["max"] = max_val
                entity_data["vital_resources"][v_def.name] = curr_data

    # 4. Calculate Consumables Max
    if stat_template.consumable_resources:
        entity_data.setdefault("consumable_resources", {})
        for c_def in stat_template.consumable_resources:
            if c_def.max_formula:
                max_val = safe_evaluate(c_def.max_formula, math_context)
                max_val = max(c_def.min_value, int(max_val))
                
                curr_data = entity_data["consumable_resources"].get(c_def.name, {})
                if not curr_data:
                    curr_data = {"current": max_val, "max": max_val}
                else:
                    curr_data["max"] = max_val
                entity_data["consumable_resources"][c_def.name] = curr_data

    return entity_data
