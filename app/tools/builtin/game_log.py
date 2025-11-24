from typing import Any, List
from app.tools.builtin.memory_upsert import handler as memory_upsert

def handler(
    content: str,
    category: str = "event",
    tags: List[str] = None,
    **context: Any
) -> dict:
    """
    Logs an event, fact, or quest update to the memory system.
    Categories: 'event' (episodic), 'fact' (semantic), 'quest' (semantic+tag).
    """
    kind_map = {
        "event": "episodic",
        "fact": "semantic",
        "quest": "semantic"
    }
    kind = kind_map.get(category, "episodic")
    
    return memory_upsert(kind=kind, content=content, tags=tags, priority=3, **context)
