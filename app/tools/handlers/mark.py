import logging
from typing import Optional
from app.services.state_service import get_entity, set_entity
from app.prefabs.validation import validate_entity, get_path, set_path
from app.prefabs import SystemManifest

logger = logging.getLogger(__name__)


def handler(path: str, count: int = 1, **context) -> dict:
    """
    Handler for 'mark' tool.
    Manipulates tracks, then runs validation.
    """
    session_id = context.get("session_id")
    db = context.get("db_manager")
    manifest: Optional[SystemManifest] = context.get("manifest")

    entity_type = "character"
    entity_key = "player"

    entity = get_entity(session_id, db, entity_type, entity_key)
    track = get_path(entity, path)

    if not isinstance(track, list):
        return {"error": f"Path '{path}' is not a track/list."}

    # 1. Apply Logic
    changed = 0
    if count > 0:
        for i in range(len(track)):
            if changed >= count:
                break
            if track[i] is False:
                track[i] = True
                changed += 1
    elif count < 0:
        to_clear = abs(count)
        for i in range(len(track) - 1, -1, -1):
            if changed >= to_clear:
                break
            if track[i] is True:
                track[i] = False
                changed += 1

    set_path(entity, path, track)

    # 2. RUN VALIDATION PIPELINE
    validated_entity, corrections = validate_entity(entity, manifest)

    # 3. Save
    set_entity(session_id, db, entity_type, entity_key, validated_entity)

    # 4. Report
    final_track = get_path(validated_entity, path)
    total_filled = sum(1 for x in final_track if x)

    return {
        "path": path,
        "marked": changed if count > 0 else -changed,
        "total_filled": total_filled,
        "visual": "".join(["[x]" if x else "[ ]" for x in final_track]),
        "corrections": corrections,
    }
