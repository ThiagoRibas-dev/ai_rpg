schema = {
    "name": "memory.delete",
    "description": "Delete a memory that is no longer relevant or was incorrect. Use sparingly - updating is usually better than deleting.",
    "parameters": {
        "type": "object",
        "properties": {
            "memory_id": {"type": "integer"}
        },
        "required": ["memory_id"]
    }
}

def handler(memory_id: int, **context) -> dict:
    """
    Delete a memory. Context should contain session_id and db_manager.
    """
    session_id = context.get("session_id")
    db_manager = context.get("db_manager")
    
    if not session_id or not db_manager:
        raise ValueError("Missing session context")
    
    # Verify memory belongs to this session
    existing = db_manager.get_memory_by_id(memory_id)
    if not existing or existing.session_id != session_id:
        raise ValueError(f"Memory {memory_id} not found in current session")
    
    db_manager.delete_memory(memory_id)
    # Remove from embeddings if available
    vs = context.get("vector_store")
    try:
        if vs:
            vs.delete_memory(session_id, memory_id)
    except Exception:
        pass

    return {"id": memory_id, "deleted": True}
