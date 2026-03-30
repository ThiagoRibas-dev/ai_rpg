
from typing import Any

from app.models.vocabulary import MemoryKind
from app.tools.builtin.memory_upsert import handler as memory_upsert


def handler(
    content: str,
    kind: MemoryKind = MemoryKind.EPISODIC,
    tags: list[str] | None = None,
    **context: Any
) -> dict:
    """
    Handler for 'note' tool. Wrapper around memory_upsert.
    """
    result = memory_upsert(kind=kind, content=content, tags=tags, priority=3, **context)

    # Update Entity Index
    session_id = context.get("session_id")
    db = context.get("db_manager")
    if session_id and db:
        from app.services.entity_index import add_memory
        title = content[:60].replace("\n", " ")
        add_memory(session_id, db, kind, title)

    return result
