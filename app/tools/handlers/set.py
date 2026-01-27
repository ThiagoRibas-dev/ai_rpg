import logging
from typing import Any, Optional
from app.services.state_service import get_entity, set_entity
from app.prefabs.validation import validate_entity, get_path, set_path
from app.prefabs.manifest import SystemManifest

logger = logging.getLogger(__name__)

def handler(path: str, value: Any, reason: str = "", **context: Any) -> dict:
    """
    Handler for 'set' tool.
    Sets value directly, then runs full validation pipeline.
    """
    session_id = context.get("session_id")
    db = context.get("db_manager")
    manifest: Optional[SystemManifest] = context.get("manifest")

    parts = path.split(".")
    
    # Check if path starts with valid entity type/id (e.g. "character.player.stats...")
    # This is a heuristic: if we have at least 3 parts (type.id.field), treat as absolute.
    if len(parts) >= 3 and parts[0] in ["character", "location", "item", "quest"]:
        entity_type = parts[0]
        entity_key = parts[1]
        relative_path = ".".join(parts[2:])
    else:
        # Legacy/Default behavior
        entity_type = "character"
        entity_key = "player"
        relative_path = path

    entity = get_entity(session_id, db, entity_type, entity_key)
    if not entity:
        return {"error": f"Entity {entity_type}:{entity_key} not found"}

    old_val = get_path(entity, relative_path)

    # 1. Apply Set
    if not set_path(entity, relative_path, value):
        return {"error": f"Failed to set path: {relative_path}"}

    # 2. RUN VALIDATION PIPELINE
    validated_entity, corrections = validate_entity(entity, manifest)

    # 3. Save
    set_entity(session_id, db, entity_type, entity_key, validated_entity)

    # 4. Report
    final_val = get_path(validated_entity, relative_path)

    return {
        "path": relative_path,
        "old_value": old_val,
        "new_value": final_val,
        "corrections": corrections,
        "reason": reason
    }
