
schema = {
    "name": "memory.upsert",
    "description": "Create a new memory entry. Use this to remember important facts, events, character details, or user preferences.",
    "parameters": {
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": ["episodic", "semantic", "lore", "user_pref"]},
            "content": {"type": "string"},
            "priority": {"type": "integer", "minimum": 1, "maximum": 5},
            "tags": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["kind", "content"]
    }
}

def handler(kind: str, content: str, priority: int = 3, tags: list[str] | None = None, 
            **context) -> dict:
    """
    Create a memory. Context should contain session_id and db_manager.
    """
    session_id = context.get("session_id")
    db_manager = context.get("db_manager")
    
    if not session_id or not db_manager:
        raise ValueError("Missing session context")
    
    memory = db_manager.create_memory(session_id, kind, content, priority, tags or [])
    
    return {
        "id": memory.id,
        "created": True,
        "kind": kind,
        "priority": priority
    }