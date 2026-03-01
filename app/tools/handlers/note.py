
from typing import Any, List
from app.tools.builtin.memory_upsert import handler as memory_upsert
from app.models.vocabulary import MemoryKind

def handler(
    content: str,
    kind: MemoryKind = MemoryKind.EPISODIC,
    tags: List[str] = None,
    **context: Any
) -> dict:
    """
    Handler for 'note' tool. Wrapper around memory_upsert.
    """
    return memory_upsert(kind=kind, content=content, tags=tags, priority=3, **context)
