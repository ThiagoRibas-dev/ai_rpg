import logging
from typing import Dict, Any
from simpleeval import simple_eval

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
    Legacy helper. Derived stats are now handled by the manifest validation pipeline
    (validate_entity with SystemManifest). This function is kept as a no-op for
    backward compatibility.
    """
    return entity_data
