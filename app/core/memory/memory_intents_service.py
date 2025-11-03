import logging
from typing import List, Dict, Any
from app.io.schemas import MemoryIntent

class MemoryIntentsService:
    """Applies memory intents using the tools registry."""
    def __init__(self, tool_registry, db_manager, vector_store, logger: logging.Logger | None = None):
        self.tools = tool_registry
        self.db = db_manager
        self.vs = vector_store
        self.logger = logger or logging.getLogger(__name__)

    def apply(self, memory_intents: List[MemoryIntent] | None, session, tool_event_callback=None):
        if not memory_intents:
            return
        for mem in memory_intents:
            try:
                args: Dict[str, Any] = {"kind": mem.kind, "content": mem.content}
                if mem.priority is not None:
                    args["priority"] = int(mem.priority)
                args["tags"] = list(mem.tags) if mem.tags is not None else []
                ctx = {"session_id": session.id, "db_manager": self.db, "vector_store": self.vs}
                result = self.tools.execute_tool("memory.upsert", args, context=ctx)
                if tool_event_callback:
                    tool_event_callback(f"memory.upsert ✓ -> {result}")
            except Exception as e:
                self.logger.error(f"Memory intent error: {e}")
