
def handler(
    kind: str | None = None,
    tags: list[str] | None = None,
    query_text: str | None = None,
    time_query: str | None = None,
    limit: int = 5,
    semantic: bool = False,
    **context,
) -> list[dict]:
    """
    Query memories. Context should contain session_id and db_manager.
    """
    session_id = context.get("session_id")
    db_manager = context.get("db_manager")

    if not session_id or not db_manager:
        raise ValueError("Missing session context")

    # Start with SQL filters
    memories = db_manager.memories.query(
        session_id, kind=kind, tags=tags, time_query=time_query, query_text=query_text, limit=limit
    )

    # If semantic requested and vector store available, blend with semantic top-k
    vs = context.get("vector_store")
    if semantic and vs and (query_text or tags or kind):
        q = query_text or " ".join((tags or [])) or (kind or "")
        sem = vs.search_memories(session_id, q, k=limit * 2)
        by_id = {m.id: m for m in memories}
        # Re-rank: prefer semantic hits, then fall back to SQL list
        ranked: list[dict] = []
        seen: set[int] = set()
        for hit in sem:
            mid = int(hit["memory_id"])
            if mid in by_id and mid not in seen:
                m = by_id[mid]
                ranked.append(m)
                seen.add(mid)
        for m in memories:
            if m.id not in seen:
                ranked.append(m)
        memories = ranked[:limit]

    # Update access tracking
    for mem in memories:
        db_manager.update_memory_access(mem.id)

    results = []
    for mem in memories:
        results.append(
            {
                "id": mem.id,
                "kind": mem.kind,
                "content": mem.content,
                "priority": mem.priority,
                "tags": mem.tags_list(),
                "created_at": mem.created_at,
                "access_count": mem.access_count,
            }
        )

    return {"memories": results, "count": len(results)}
