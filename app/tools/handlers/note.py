
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

    # Map simple kinds to memory types
    kind_map = {
        "event": "episodic",
        "fact": "semantic",
        "lore": "lore",
    }
    mem_kind = kind_map.get(kind, "episodic")

    return memory_upsert(kind=mem_kind, content=content, tags=tags, priority=3, **context)
