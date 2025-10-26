from typing import Any

schema = {
    "name": "state.apply_patch",
    "description": "Apply a JSON-like patch to an entity (MVP: in-memory).",
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

_STORE: dict[tuple[str, str], dict[str, Any]] = {}
_VERS: dict[tuple[str, str], int] = {}

def handler(entity_type: str, key: str, patch: list[dict]) -> dict:
    ek = (entity_type, key)
    entity = _STORE.get(ek, {})
    for op in patch:
        o, path, value = op.get("op"), op.get("path"), op.get("value", None)
        if o is None or path is None:
            # op and path are required by schema, but for type safety we check.
            raise ValueError("Patch op is missing required 'op' or 'path' property.")

        if o == "add":
            if path in ("", "/"):
                entity = value
            else:
                _set_path(entity, path, value, create=True)
        elif o == "replace":
            _set_path(entity, path, value, create=False)
        elif o == "remove":
            _del_path(entity, path)
        else:
            raise ValueError(f"Unsupported op: {o}")
    _STORE[ek] = entity
    _VERS[ek] = _VERS.get(ek, 0) + 1
    return {"version": _VERS[ek]}

def _set_path(obj: dict, path: str, value: Any, create: bool):
    parts = [p for p in path.split("/") if p]
    cur = obj
    for i, p in enumerate(parts):
        if i == len(parts) - 1:
            cur[p] = value
        else:
            if p not in cur:
                if not create:
                    raise KeyError(f"Missing path segment: {p}")
                cur[p] = {}
            cur = cur[p]

def _del_path(obj: dict, path: str):
    parts = [p for p in path.split("/") if p]
    cur = obj
    for i, p in enumerate(parts):
        if i == len(parts) - 1:
            cur.pop(p, None)
        else:
            cur = cur.get(p, {})