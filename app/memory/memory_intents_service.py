import logging
from typing import List
from app.llm.schemas import MemoryIntent
from app.tools.schemas import MemoryUpsert


class MemoryIntentsService:
    """Applies memory intents using the tools registry."""

    def __init__(
        self,
        tool_registry,
        db_manager,
        vector_store,
        logger: logging.Logger | None = None,
    ):
        self.tools = tool_registry
        self.db = db_manager
        self.vs = vector_store
        self.logger = logger or logging.getLogger(__name__)

    def apply(
        self,
        memory_intents: List[MemoryIntent] | None,
        session,
        tool_event_callback=None,
    ):
        if not memory_intents:
            return
        for mem in memory_intents:
            try:
                mem_call = MemoryUpsert(
                    kind=mem.kind,
                    content=mem.content,
                    priority=int(mem.priority) if mem.priority is not None else 3,
                    tags=list(mem.tags) if mem.tags is not None else [],
                )
                ctx = {
                    "session_id": session.id,
                    "db_manager": self.db,
                    "vector_store": self.vs,
                }
                result = self.tools.execute(mem_call, context=ctx)
                if tool_event_callback:
                    tool_event_callback(f"memory.upsert ✓ -> {result}")
            except Exception as e:
                self.logger.error(f"Memory intent error: {e}")
