schema = {
    "name": "memory.update",
    "description": "Update an existing memory's content, priority, or tags. Use when information changes or becomes more/less important.",
    "parameters": {
        "type": "object",
        "properties": {
            "memory_id": {"type": "integer"},
            "content": {"type": "string"},
            "priority": {"type": "integer", "minimum": 1, "maximum": 5},
            "tags": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["memory_id"]
    }
}

def handler(memory_id: int, content: str | None = None, priority: int | None = None,
            tags: list[str] | None = None, **context) -> dict:
    """
    Update a memory. Context should contain session_id and db_manager.
    """
    session_id = context.get("session_id")
    db_manager = context.get("db_manager")
    
    if not session_id or not db_manager:
        raise ValueError("Missing session context")
    
    # Verify memory belongs to this session
    existing = db_manager.get_memory_by_id(memory_id)
    if not existing or existing.session_id != session_id:
        raise ValueError(f"Memory {memory_id} not found in current session")
    
    updated = db_manager.update_memory(memory_id, content=content, priority=priority, tags=tags)

    # Update embedding if available
    vs = context.get("vector_store")
    try:
        if vs:
            vs.upsert_memory(session_id, updated.id, updated.content, updated.kind, updated.tags_list(), updated.priority)
    except Exception:
        pass
    
    return {
        "id": updated.id,
        "updated": True,
        "content": updated.content,
        "priority": updated.priority,
        "tags": updated.tags_list()
    }
