from typing import Any
from app.tools.builtin._state_storage import get_entity, set_entity

schema = {
    "name": "state.apply_patch",
    "description": "Apply a JSON-like patch to an entity (persisted to database).",
    "parameters": {
        "type": "object",
        "properties": {
            "entity_type": {"type": "string"},
            "key": {"type": "string"},
            "patch": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "op": {"type": "string"},
                        "path": {"type": "string"},
                        "value": {
                            "anyOf": [
                                {"type": "object"},
                                {"type": "array"},
                                {"type": "string"},
                                {"type": "number"},
                                {"type": "boolean"}
                            ]
                        }
                    },
                    "required": ["op", "path"]
                }
            }
        },
        "required": ["entity_type", "key", "patch"]
    }
}


def handler(entity_type: str, key: str, patch: list[dict], **context) -> dict:
    """
    Apply JSON Patch operations to a game state entity.
    
    Context must include:
        - session_id: Current session
        - db_manager: Database manager instance
    """
    session_id = context.get("session_id")
    db_manager = context.get("db_manager")
    
    if not session_id or not db_manager:
        raise ValueError("state.apply_patch requires session_id and db_manager in context")
    
    # Load entity from database
    entity = get_entity(session_id, db_manager, entity_type, key)
    
    # Apply patches sequentially
    for op in patch:
        o, path, value = op.get("op"), op.get("path"), op.get("value", None)
        
        if o is None or path is None:
            raise ValueError("Patch op is missing required 'op' or 'path' property.")

        if o == "add":
            if path in ("", "/"):
                entity = value if isinstance(value, dict) else entity
            else:
                _set_path(entity, path, value, create=True)
        
        elif o == "replace":
            if path in ("", "/"):
                entity = value if isinstance(value, dict) else entity
            else:
                _set_path(entity, path, value, create=False)
        
        elif o == "remove":
            _del_path(entity, path)
        
        else:
            raise ValueError(f"Unsupported operation: {o}")
    
    # Save back to database
    version = set_entity(session_id, db_manager, entity_type, key, entity)
    
    return {
        "success": True,
        "entity_type": entity_type,
        "key": key,
        "version": version
    }


def _set_path(obj: dict, path: str, value: Any, create: bool):
    """Set a value at a JSON path within an object."""
    parts = [p for p in path.split("/") if p]
    
    if not parts:
        raise ValueError("Cannot set empty path")
    
    cur = obj
    for i, p in enumerate(parts[:-1]):
        if p not in cur:
            if not create:
                raise KeyError(f"Missing path segment: {p}")
            cur[p] = {}
        elif not isinstance(cur[p], dict):
            raise TypeError(f"Path segment {p} is not a dict")
        cur = cur[p]
    
    # Set the final key
    final_key = parts[-1]
    cur[final_key] = value


def _del_path(obj: dict, path: str):
    """Delete a value at a JSON path within an object."""
    parts = [p for p in path.split("/") if p]
    
    if not parts:
        raise ValueError("Cannot delete empty path")
    
    cur = obj
    for p in parts[:-1]:
        if p not in cur or not isinstance(cur[p], dict):
            return  # Path doesn't exist, nothing to delete
        cur = cur[p]
    
    # Delete the final key
    final_key = parts[-1]
    cur.pop(final_key, None)
