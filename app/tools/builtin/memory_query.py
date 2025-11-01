
schema = {
    "name": "memory.query",
    "description": "Search and retrieve memories. Use this before making decisions to recall relevant past information.",
    "parameters": {
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": ["episodic", "semantic", "lore", "user_pref"]},
            "tags": {"type": "array", "items": {"type": "string"}},
            "query_text": {"type": "string"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 20}
        },
        "required": []
    }
}

def handler(kind: str | None = None, tags: list[str] | None = None, 
            query_text: str | None = None, limit: int = 5, **context) -> dict:
    """
    Query memories. Context should contain session_id and db_manager.
    """
    session_id = context.get("session_id")
    db_manager = context.get("db_manager")
    
    if not session_id or not db_manager:
        raise ValueError("Missing session context")
    
    memories = db_manager.query_memories(
        session_id, kind=kind, tags=tags, query_text=query_text, limit=limit
    )
    
    # Update access tracking
    for mem in memories:
        db_manager.update_memory_access(mem.id)
    
    results = []
    for mem in memories:
        results.append({
            "id": mem.id,
            "kind": mem.kind,
            "content": mem.content,
            "priority": mem.priority,
            "tags": mem.tags_list(),
            "created_at": mem.created_at,
            "access_count": mem.access_count
        })
    
    return {"memories": results, "count": len(results)}