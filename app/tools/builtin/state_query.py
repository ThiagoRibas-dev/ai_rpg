from typing import Any, Dict
from app.services.state_service import get_entity, get_all_of_type

def handler(entity_type: str, key: str, json_path: str, **context) -> Dict[str, Any]:
    """
    Query game state entity data.

    Special key values:
        - "*" returns all entities of the given type
        - Otherwise returns the specific entity

    Context must include:
        - session_id: Current session
        - db_manager: Database manager instance
    """
    session_id = context.get("session_id")
    db_manager = context.get("db_manager")

    if not session_id or not db_manager:
        raise ValueError("state.query requires session_id and db_manager in context")

    # Special case: query all entities of a type
    if key == "*":
        all_entities = get_all_of_type(session_id, db_manager, entity_type)
        return {"value": all_entities}

    # Query specific entity
    entity = get_entity(session_id, db_manager, entity_type, key)

    # Return root if path is empty/root
    if json_path in ("", ".", "/"):
        return {"value": entity}

    # Navigate the path
    cur: Any = entity
    for seg in [s for s in json_path.split(".") if s]:
        if isinstance(cur, dict) and seg in cur:
            cur = cur[seg]
        else:
            return {"value": None}

    return {"value": cur}
