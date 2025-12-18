import logging
from typing import Any, Optional
from app.services.state_service import get_entity, set_entity
from app.prefabs.validation import validate_entity, get_path, set_path
from app.prefabs import SystemManifest

logger = logging.getLogger(__name__)

def handler(path: str, value: Any, reason: str = "", **context) -> dict:
    """
    Handler for 'set' tool.
    Sets value directly, then runs full validation pipeline.
    """
    session_id = context.get("session_id")
    db = context.get("db_manager")
    manifest: Optional[SystemManifest] = context.get("manifest")

    entity_type = "character"
    entity_key = "player"

    entity = get_entity(session_id, db, entity_type, entity_key)
    if not entity:
        return {"error": "Entity not found"}

    old_val = get_path(entity, path)

    # 1. Apply Set
    set_path(entity, path, value)

    # 2. RUN VALIDATION PIPELINE
    validated_entity, corrections = validate_entity(entity, manifest)

    # 3. Save
    set_entity(session_id, db, entity_type, entity_key, validated_entity)

    # 4. Report
    final_val = get_path(validated_entity, path)

    return {
        "path": path,
        "old_value": old_val,
        "new_value": final_val,
        "corrections": corrections,
        "reason": reason
    }
