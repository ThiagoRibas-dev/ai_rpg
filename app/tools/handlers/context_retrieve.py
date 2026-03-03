from typing import Any, List, Optional
from app.context.memory_retriever import MemoryRetriever
from app.models.session import Session
from app.models.message import Message


def handler(
    query: str, kinds: Optional[List[str]] = None, limit: int = 8, **context: Any
) -> dict:
    session_id = context.get("session_id")
    db = context.get("db_manager")
    vs = context.get("vector_store")

    if not session_id or not db:
        return {"error": "Missing session context"}

    mr = MemoryRetriever(db, vs)

    sess = Session("synthetic_retrieval")
    sess.id = session_id

    # Build minimal "recent_messages" so MemoryRetriever can score keywords/semantic
    recent = [Message(role="user", content=query)]

    mems = mr.get_relevant(sess, recent_messages=recent, kinds=kinds, limit=limit)
    text = mr.format_for_prompt(mems, title="RETRIEVED CONTEXT")

    # Extract memory IDs from the MemoryKind objects
    memory_ids = []
    if mems:
        for mem_list in mems.values():
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
