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


def handler(
    kind: str, content: str, priority: int = 3, tags: list[str] | None = None, **context
) -> dict:
    """
    Create a memory. Context should contain session_id and db_manager.

    ✅ FIX: Deduplication logic moved here from registry.
    """
    session_id = context.get("session_id")
    db_manager = context.get("db_manager")

    if not session_id or not db_manager:
        raise ValueError("Missing session context")

    # ✅ MOVED FROM REGISTRY: Check for near-duplicates
    vs = context.get("vector_store")
    if vs:
        try:
            # Find near-duplicates using semantic search
            sem_results = vs.search_memories(session_id, content, k=5)

            for hit in sem_results:
                mid = int(hit["memory_id"])
                existing = db_manager.get_memory_by_id(mid)
                if not existing:
                    continue

                # cosine distance ~ 0 => very similar; treat <=0.10 as duplicate
                dist = hit.get("distance") or 0.0
                if dist <= 0.10 and existing.kind == kind:
                    # Found duplicate - update instead of create
                    merged_tags = sorted(
                        set((existing.tags_list() or []) + (tags or []))
                    )
                    new_priority = min(5, max(existing.priority, priority))

                    # Update existing memory
                    updated = db_manager.update_memory(
                        existing.id,
                        content=content if content != existing.content else None,
                        priority=new_priority,
                        tags=merged_tags,
                    )

                    # Update embedding
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
            import logging

            logging.getLogger(__name__).debug(
                f"Memory deduplication failed: {e}", exc_info=True
            )

    # No duplicate found - create new memory
    memory = db_manager.create_memory(session_id, kind, content, priority, tags or [])

    # If a vector store is available, embed
    if vs:
        try:
            vs.upsert_memory(session_id, memory.id, content, kind, tags or [], priority)
        except Exception:
            pass

    return {
        "id": memory.id,
        "created": True,
        "kind": kind,
        "priority": priority,
        "content": content,
        "tags": tags or [],
    }
