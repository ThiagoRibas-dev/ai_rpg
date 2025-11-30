import logging
from typing import Dict, Any
from simpleeval import simple_eval
from app.models.stat_block import StatBlockTemplate

logger = logging.getLogger(__name__)

def safe_evaluate(expression: str, context: Dict[str, Any]) -> int | float:
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
    if not entity_data or not stat_template:
        return entity_data

    math_context = {}
    
    # 1. Load Raw Values into Context
    values = entity_data.get("values", {})
    for key, val in values.items():
        math_context[key] = val
        # Legacy D20 helper (optional, can be removed if prompt handles formula generation well)
        if isinstance(val, int):
            math_context[f"{key}_mod"] = (val - 10) // 2

    # 2. Calculate Derived Values
    for key, def_ in stat_template.values.items():
        if def_.calculation:
            res = safe_evaluate(def_.calculation, math_context)
            # Update entity data
            values[key] = int(res) if def_.data_type == "integer" else res
            # Update math context for subsequent formulas
            math_context[key] = values[key]
    
    entity_data["values"] = values

    # 3. Update Gauge Maxima
    gauges = entity_data.get("gauges", {})
    for key, def_ in stat_template.gauges.items():
        if def_.max_formula:
            max_val = int(safe_evaluate(def_.max_formula, math_context))
            max_val = max(def_.min_val, max_val)
            
            gauge_data = gauges.get(key, {})
            if not gauge_data:
                gauge_data = {"current": max_val, "max": max_val}
            else:
                gauge_data["max"] = max_val
            
            gauges[key] = gauge_data
            
    entity_data["gauges"] = gauges

    return entity_data
