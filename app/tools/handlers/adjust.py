import logging
from typing import Optional, Any
from app.services.state_service import get_entity, set_entity
from app.prefabs.validation import validate_entity, get_path, set_path
from app.prefabs.manifest import SystemManifest

logger = logging.getLogger(__name__)

def handler(path: str, delta: int | float, reason: str = "", **context: Any) -> dict:
    """
    Handler for 'adjust' tool.
    Applies delta to a numeric field, then runs full validation pipeline.
    """
    session_id = context.get("session_id")
    db = context.get("db_manager")
    # Executor passes the full manifest object here
    manifest: Optional[SystemManifest] = context.get("manifest")

    entity_type = "character"
    entity_key = "player"
    target_path = path

    # 1. Get Entity
    entity = get_entity(session_id, db, entity_type, entity_key)
    if not entity:
        return {"error": "Entity not found"}

    # 2. Get Current Value
    current_val = get_path(entity, target_path)
    
    # Handle Pools (path.current logic)
    actual_path = target_path
    if isinstance(current_val, dict) and "current" in current_val:
        actual_path = f"{target_path}.current"
        current_val = current_val["current"]

    # Coerce to number if possible (handle string numbers)
    try:
        current_val = float(current_val)
        if current_val.is_integer():
            current_val = int(current_val)
    except (ValueError, TypeError):
        pass

    if not isinstance(current_val, (int, float)):
        return {"error": f"Path '{actual_path}' is not numeric ({type(current_val)})."}

    # 3. Apply Delta
    new_val = current_val + delta
    set_path(entity, actual_path, new_val)

    # 4. RUN VALIDATION PIPELINE (The Lego Protocol)
    # This recalculates derived stats and clamps values (e.g. HP <= Max)
    validated_entity, corrections = validate_entity(entity, manifest)

    # 5. Save
    set_entity(session_id, db, entity_type, entity_key, validated_entity)

    # 6. Report
    final_val = get_path(validated_entity, actual_path)
    
    return {
        "path": actual_path,
        "old_value": current_val,
        "delta": delta,
        "new_value": final_val,
        "corrections": corrections,
        "reason": reason
    }
