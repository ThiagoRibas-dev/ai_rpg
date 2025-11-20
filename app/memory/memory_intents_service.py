import logging
import queue
from typing import List, Optional

from app.llm.schemas import MemoryIntent
from app.tools.schemas import MemoryUpsert


class MemoryIntentsService:
    """Applies memory intents using the tools registry."""

    def __init__(
        self,
        tool_registry,
        db_manager,
        vector_store,
        ui_queue: Optional[queue.Queue] = None,  # Added dependency
        logger: logging.Logger | None = None,
    ):
        self.tools = tool_registry
        self.db = db_manager
        self.vs = vector_store
        self.ui_queue = ui_queue
        self.logger = logger or logging.getLogger(__name__)

    def apply(
        self,
        memory_intents: List[MemoryIntent] | None,
        session,
        tool_event_callback=None,
    ):
        if not memory_intents:
            return

        changes_made = False

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

                # Execute directly via registry (bypasses ToolExecutor)
                result = self.tools.execute(mem_call, context=ctx)
                changes_made = True

                if tool_event_callback:
                    tool_event_callback(f"memory.upsert âœ“ -> {result}")
            except Exception as e:
                self.logger.error(f"Memory intent error: {e}", exc_info=True)

        # Trigger UI refresh if we processed any memories
        if changes_made and self.ui_queue:
            self.ui_queue.put({"type": "refresh_memory_inspector"})
