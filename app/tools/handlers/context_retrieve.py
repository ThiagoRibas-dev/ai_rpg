from typing import Any

from app.context.memory_retriever import MemoryRetriever
from app.models.session import Session


def handler(
    query: str, kinds: list[str] | None = None, limit: int = 8, **context: Any
) -> dict:
    session_id = context.get("session_id")
    db = context.get("db_manager")
    vs = context.get("vector_store")

    if not session_id or not db:
        return {"error": "Missing session context"}

    mr = MemoryRetriever(db, vs)

    sess = Session("synthetic_retrieval")
    sess.id = session_id

    # 1. Capture Pre-fetched Context
    pre_fetched: dict[str, list[Any]] = context.get("pre_fetched_mems") or {}
    exclude_ids = []
    for mem_list in pre_fetched.values():
        if not mem_list:
            continue
        for mem in mem_list:
            if hasattr(mem, "id"):
                exclude_ids.append(mem.id)
            elif isinstance(mem, dict) and "id" in mem:
                exclude_ids.append(mem["id"])

    # 2. Retrieve NEW context
    from app.models.vocabulary import MemoryKind
    kind_enums = [MemoryKind(k) for k in kinds] if kinds else None

    new_mems = mr.get_relevant(
        sess,
        recent_messages=[],
        kinds=kind_enums,
        limit=limit,
        exclude_ids=exclude_ids,
        explicit_query=query
    )

    # 3. Consolidate: Pre-fetched + New
    consolidated = {}
    # Start with pre-fetched
    for k, v in pre_fetched.items():
        consolidated[k] = list(v)

    # Add new (already filtered by exclude_ids)
    for k, v in new_mems.items():
        if k not in consolidated:
            consolidated[k] = []
        consolidated[k].extend(v)

    # 4. Format for prompt
    text = mr.format_for_prompt(consolidated, title="RETRIEVED CONTEXT")

    # Extract ALL memory IDs for the metadata
    memory_ids = []
    for mem_list in consolidated.values():
        for mem in mem_list:
            if hasattr(mem, 'id'):
                memory_ids.append(mem.id)
            elif isinstance(mem, dict) and 'id' in mem:
                memory_ids.append(mem['id'])

    return {
        "query": query,
        "kinds": kinds or [],
        "limit": limit,
        "text": text,
        "memory_ids": memory_ids
    }
