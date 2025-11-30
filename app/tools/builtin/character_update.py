import logging

from typing import Any, Dict, List
from app.tools.builtin._state_storage import get_entity, set_entity
from app.utils.state_validator import StateValidator
from app.utils.math_engine import recalculate_derived_stats

logger = logging.getLogger(__name__)


def handler(character_key: str, updates: List[Dict[str, Any]], **context) -> dict:
    session_id = context["session_id"]
    db = context["db_manager"]

    entity = get_entity(session_id, db, "character", character_key)
    if not entity:
        raise ValueError(f"Character {character_key} not found")

    tid = entity.get("template_id")
    template = db.stat_templates.get_by_id(tid) if tid else None
    if not template:
        raise ValueError("No template found")

    validator = StateValidator(template)

    for update in updates:
        key = update["key"]
        val = update["value"]

        try:
            kind = validator.validate_update(key, val)
        except ValueError as e:
            logger.warning(f"Invalid update: {e}")
            continue

        if kind == "fundamental":
            entity.setdefault("fundamentals", {})[key] = val
        elif kind == "derived":
            # Allow manual override, though recalc might overwrite it if logic runs
            entity.setdefault("derived", {})[key] = val
        elif kind == "gauge":
            gauge_data = entity.setdefault("gauges", {}).setdefault(
                key, {"current": 0, "max": 0}
            )
            if isinstance(val, (int, float)):
                gauge_data["current"] = val
            elif isinstance(val, dict):
                gauge_data.update(val)

    entity = recalculate_derived_stats(entity, template)
    set_entity(session_id, db, "character", character_key, entity)

    return {"success": True, "updates": len(updates)}
