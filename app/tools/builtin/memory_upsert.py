import hashlib
import json

schema = {
    "name": "memory.upsert",
    "description": "Upsert a memory entry (MVP: in-memory, content+tags dedupe).",
    "parameters": {
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": ["episodic", "semantic", "lore", "user_pref"]},
            "content": {"type": "string"},
            "priority": {"type": "integer"},
            "tags": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["kind", "content"]
    }
}

_MEM: dict[str, dict] = {}

def handler(kind: str, content: str, priority: int = 3, tags: list[str] | None = None) -> dict:
    tags = tags or []
    key = hashlib.sha1(json.dumps({"k": kind, "c": content, "t": tags}, sort_keys=True).encode()).hexdigest()
    deduped = key in _MEM
    _MEM[key] = {"kind": kind, "content": content, "priority": priority, "tags": tags}
    return {"id": key, "deduped": deduped}