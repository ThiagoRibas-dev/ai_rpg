import logging

schema = {
    "name": "memory.upsert",
    "description": "Create a new memory entry. Use this to remember important facts, events, character details, or user preferences.",
    "parameters": {
        "type": "object",
        "properties": {
            "kind": {
                "type": "string",
                "enum": ["episodic", "semantic", "lore", "user_pref"],
            },
            "content": {"type": "string"},
            "priority": {"type": "integer", "minimum": 1, "maximum": 5},
            "tags": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["kind", "content"],
    },
}

logger = logging.getLogger(__name__)

def handler(
    kind: str, content: str, priority: int = 3, tags: list[str] | None = None, **context
) -> dict:
    """
    Create a memory. Context should contain session_id and db_manager.
    Includes logic to deduplicate against existing memories using Vector Search.
    """
    session_id = context.get("session_id")
    db_manager = context.get("db_manager")
    fictional_time = context.get("current_game_time")

    if not session_id or not db_manager:
        raise ValueError("Missing session context")

    vs = context.get("vector_store")
    
    # --- Deduplication Logic ---
    if vs:
        try:
            # Find near-duplicates using semantic search
            sem_results = vs.search_memories(session_id, content, k=5)

            for hit in sem_results:
                mid = int(hit["memory_id"])
                
                # FIX: Use correct repository accessor (db.memories.get_by_id)
                existing = db_manager.memories.get_by_id(mid)
                if not existing:
                    continue

                # cosine distance ~ 0 => very similar; treat <=0.12 as duplicate
                dist = hit.get("distance") or 0.0
                if dist <= 0.12 and existing.kind == kind:
                    # Found duplicate - update instead of create
                    merged_tags = sorted(
                        set((existing.tags_list() or []) + (tags or []))
                    )
                    new_priority = min(5, max(existing.priority, priority))

                    # FIX: Use correct repository accessor (db.memories.update)
                    updated = db_manager.memories.update(
                        existing.id,
                        content=content if content != existing.content else None,
                        priority=new_priority,
                        tags=merged_tags,
                    )

                    # Update embedding in Vector Store
                    if updated:
                        vs.upsert_memory(
                            session_id,
                            updated.id,
                            updated.content,
                            updated.kind,
                            updated.tags_list(),
                            updated.priority,
                        )

                    return {
                        "id": updated.id,
                        "created": False,
                        "updated": True,
                        "kind": kind,
                        "priority": new_priority,
                        "content": content,
                        "tags": merged_tags,
                        "note": f"Merged with existing memory {existing.id}",
                    }
        except Exception as e:
            logger.warning(f"Memory deduplication failed: {e}", exc_info=True)

    # --- Creation Logic ---
    memory = db_manager.memories.create(
        session_id, kind, content, priority, tags or [], fictional_time=fictional_time
    )

    # If a vector store is available, embed new memory
    if vs:
        try:
            vs.upsert_memory(session_id, memory.id, content, kind, tags or [], priority)
        except Exception as e:
            logger.error(f"Failed to embed new memory: {e}")

    return {
        "id": memory.id,
        "created": True,
        "kind": kind,
        "priority": priority,
        "content": content,
        "tags": tags or [],
    }
