# app/tools/builtin/state_query.py
from typing import Any, Dict
from .state_apply_patch import _STORE

schema = {
    "name": "state.query",
    "description": "Read data from in-memory state using a simple dotted path (MVP).",
    "parameters": {
        "type": "object",
        "properties": {
            "entity_type": {"type": "string"},
            "key": {"type": "string"},
            "json_path": {"type": "string", "description": "Dot path, e.g., 'attributes.hp' or '.' for root"}
        },
        "required": ["entity_type", "key", "json_path"]
    }
}

def handler(entity_type: str, key: str, json_path: str) -> Dict[str, Any]:
    entity = _STORE.get((entity_type, key), {})
    if json_path in ("", ".", "/"):
        return {"value": entity}

    cur: Any = entity
    for seg in [s for s in json_path.split(".") if s]:
        if isinstance(cur, dict) and seg in cur:
            cur = cur[seg]
        else:
            return {"value": None}
    return {"value": cur}
