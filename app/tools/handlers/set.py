import logging
from typing import TYPE_CHECKING, Any, cast

from app.models.vocabulary import EntityKey, EntityType
from app.prefabs.manifest import SystemManifest
from app.prefabs.validation import get_path, set_path, validate_entity
from app.services.state_service import get_entity, set_entity

if TYPE_CHECKING:
    from app.database.db_manager import DBManager

logger = logging.getLogger(__name__)

def handler(path: str, value: Any, target: str = EntityKey.PLAYER, reason: str = "", **context: Any) -> dict:
    """
    Handler for 'set' tool.
    Sets value directly, then runs full validation pipeline.
    """
    session_id = context.get("session_id")
    db = context.get("db_manager")
    manifest: SystemManifest | None = context.get("manifest")

    if not isinstance(session_id, int) or db is None:
        return {"error": "Missing session_id or db_manager in context"}

    db = cast("DBManager", db)

    parts = path.split(".")

    # Check if path starts with valid entity type/id (e.g. "character.player.stats...")
    # This is a heuristic: if we have at least 3 parts (type.id.field), treat as absolute.
    if len(parts) >= 3 and parts[0] in [e.value for e in EntityType]:
        entity_type = parts[0]
        entity_key = parts[1]
        relative_path = ".".join(parts[2:])
    else:
        # Legacy/Default behavior
        entity_type = EntityType.CHARACTER
        entity_key = target
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
