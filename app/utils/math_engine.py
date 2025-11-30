import logging
from typing import Dict, Any
from simpleeval import simple_eval
from app.models.stat_block import StatBlockTemplate

logger = logging.getLogger(__name__)


def safe_evaluate(expression: str, context: Dict[str, Any]) -> int | float:
    if not expression or expression == "0" or expression == "null":
        return 0
    try:
        # Convert all context values to float for math safety
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


def recalculate_derived_stats(
    entity_data: Dict[str, Any], stat_template: StatBlockTemplate
) -> Dict[str, Any]:
    if not entity_data or not stat_template:
        return entity_data

    math_context = {}

    # 1. Load Fundamentals
    fundamentals = entity_data.get("fundamentals", {})
    for key, val in fundamentals.items():
        # CHECK TEMPLATE TYPE BEFORE FORCING FLOAT
        stat_def = stat_template.fundamentals.get(key)

        # SAFEGUARD: Only put numbers into the math context
        if stat_def and stat_def.data_type in ["integer", "float"]:
            try:
                math_context[key] = float(val)
            except Exception as e:
                logger.warning(f"Invalid fundamental '{key}' value '{val}': {e}")
                math_context[key] = 0.0
        elif stat_def and stat_def.data_type == "die":
            # OPTIONAL: Extract max value from "d20" -> 20 for math?
            # For now, just ignore or store 0
            math_context[key] = 0.0
        else:
            # Pass strings/bools through for display or non-math logic
            math_context[key] = val

        # Legacy D20 helper
        if isinstance(val, int) and val > 0:
            math_context[f"{key}_mod"] = (val - 10) // 2

    # 2. Calculate Derived Values
    derived = entity_data.get("derived", {})
    for key, def_ in stat_template.derived.items():
        if def_.calculation:
            res = safe_evaluate(def_.calculation, math_context)
            final_val = int(res) if def_.data_type == "integer" else res
            derived[key] = final_val
            # Add to context for subsequent formulas
            math_context[key] = final_val

    entity_data["derived"] = derived

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
