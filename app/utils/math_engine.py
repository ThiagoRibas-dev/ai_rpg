import logging
from typing import Dict, Any
from simpleeval import simple_eval
from app.models.sheet_schema import CharacterSheetSpec

logger = logging.getLogger(__name__)


def safe_evaluate(expression: str, context: Dict[str, Any]) -> int | float:
    if not expression or expression == "0" or expression == "null":
        return 0
    try:
        # Convert context to float
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
    entity_data: Dict[str, Any], template: Any
) -> Dict[str, Any]:
    """
    Recalculates formulas defined in the CharacterSheetSpec.
    """
    if not entity_data or not template:
        return entity_data

    # Check if it's the new spec
    if not isinstance(template, CharacterSheetSpec):
        # Fallback for old templates if any exist (Legacy support)
        return entity_data

    math_context = {}

    # 1. Harvest Values for Context
    # We flatten the entity data categories into a single context for formulas
    # e.g. attributes.str -> "str" in context
    cats = ["attributes", "resources", "skills", "features"]

    for cat in cats:
        data = entity_data.get(cat, {})
        for key, val in data.items():
            if isinstance(val, (int, float)):
                math_context[key] = val
            elif isinstance(val, dict) and "current" in val:
                # For pools, expose current and max
                math_context[f"{key}_current"] = val.get("current", 0)
                math_context[f"{key}_max"] = val.get("max", 0)
                # Also expose base key as current for convenience
                math_context[key] = val.get("current", 0)
            elif isinstance(val, str) and val.isdigit():
                math_context[key] = float(val)

    # 2. Iterate Template to find Formulas
    # Helper to process a category
    spec_dict = template.model_dump()

    for cat_name, cat_def in spec_dict.items():
        if "fields" not in cat_def:
            continue

        fields = cat_def["fields"]
        entity_cat = entity_data.setdefault(cat_name, {})

        for field_key, field_def in fields.items():
            # Atom Formula
            if field_def.get("container_type") == "atom":
                formula = field_def.get("formula")
                if formula:
                    res = safe_evaluate(formula, math_context)
                    entity_cat[field_key] = int(res)  # Assume int for stats usually
                    math_context[field_key] = res  # Update context for subsequent deps

            # Molecule Formula (e.g. Max HP)
            elif field_def.get("container_type") == "molecule":
                components = field_def.get("components", {})
                entity_mol = entity_cat.setdefault(field_key, {})

                for comp_key, comp_def in components.items():
                    formula = comp_def.get("formula")
                    if formula:
                        res = safe_evaluate(formula, math_context)
                        entity_mol[comp_key] = int(res)
                        math_context[f"{field_key}_{comp_key}"] = res

    return entity_data
