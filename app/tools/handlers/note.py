
from typing import Any, List
from app.tools.builtin.memory_upsert import handler as memory_upsert

def handler(
    content: str,
    kind: str = "event",
    tags: List[str] = None,
    **context: Any
) -> dict:
    """
    Handler for 'note' tool. Wrapper around memory_upsert.
    """
    # Map simple kinds to memory types if needed, though they match 1:1 currently
    return memory_upsert(kind=kind, content=content, tags=tags, priority=3, **context)
