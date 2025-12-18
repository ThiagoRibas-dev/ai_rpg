import logging
import queue
from typing import Any, Dict, List, Tuple

from pydantic import BaseModel

from app.tools.schemas import Roll, Note


class ToolExecutor:
    """
    Executes tool calls from the LLM using type-based dispatch.
    Integrates with UI queue and handles per-tool hooks.
    """

    def __init__(
        self,
        tool_registry,
        db_manager,
        vector_store,
        ui_queue: queue.Queue | None = None,
        logger: logging.Logger | None = None,
    ):
        self.tools = tool_registry
        self.db = db_manager
        self.vs = vector_store
        self.ui_queue = ui_queue
        self.logger = logger or logging.getLogger(__name__)

    def execute(
        self,
        tool_calls: List[BaseModel],
        session,
        manifest: Dict[str, Any],
        tool_budget: int,
        current_game_time: str | None = None,
        extra_context: Dict[str, Any] | None = None,
        turn_id: str | None = None,
    ) -> Tuple[List[Dict[str, Any]], bool]:
        results: List[Dict[str, Any]] = []
        memory_tool_used = False

        if not tool_calls:
            return results, memory_tool_used

        ctx = {
            "session_id": session.id,
            "db_manager": self.db,
            "vector_store": self.vs,
            "manifest": manifest,  # This needs to be the SystemManifest object ideally
            "current_game_time": current_game_time,
            "ui_queue": self.ui_queue,
        }

        if extra_context:
            ctx.update(extra_context)

        for i, call in enumerate(tool_calls[:tool_budget]):
            tool_name = call.name

            # Notify UI
            if self.ui_queue:
                try:
                    self.ui_queue.put(
                        {
                            "type": "tool_call",
                            "name": tool_name,
                            "args": call.model_dump(exclude={"name"}),
                            "turn_id": turn_id,
                        }
                    )
                except Exception:
                    pass

            try:
                # EXECUTE
                result = self.tools.execute(call, context=ctx)

                # Special UI Events
                if isinstance(call, Roll) and self.ui_queue:
                    self.ui_queue.put(
                        {
                            "type": "dice_roll",
                            "spec": call.formula,
                            "rolls": result.get("rolls", []),
                            "total": result.get("total", 0),
                            "turn_id": turn_id,
                        }
                    )

                results.append(
                    {
                        "name": tool_name,
                        "arguments": call.model_dump(exclude={"name"}),
                        "result": result,
                    }
                )

                # UI Success
                if self.ui_queue:
                    self.ui_queue.put(
                        {
                            "type": "tool_result",
                            "result": result,
                            "is_error": False,
                            "turn_id": turn_id,
                        }
                    )

                # Post Hooks
                self._post_hook(tool_name, result, session, turn_id)

                # Check if a memory tool was used (for refreshing context)
                if isinstance(call, Note):
                    memory_tool_used = True

            except Exception as e:
                self.logger.error(f"Tool error {tool_name}: {e}", exc_info=True)
                results.append({"name": tool_name, "error": str(e)})
                if self.ui_queue:
                    self.ui_queue.put(
                        {
                            "type": "tool_result",
                            "result": str(e),
                            "is_error": True,
                            "turn_id": turn_id,
                        }
                    )

        return results, memory_tool_used

    def _post_hook(self, tool_name: str, result: Any, session, turn_id: str | None):
        """Update UI based on tool results."""

        # State Changes -> Refresh Inspectors
        if tool_name in [
            "adjust",
            "set",
            "mark",
            "entity.update",
            "inventory.add_item",
        ]:
            if self.ui_queue:
                self.ui_queue.put({"type": "state_changed", "turn_id": turn_id})

        # Memory -> Refresh Log
        if tool_name in ["note", "game.log", "memory.upsert"]:
            if self.ui_queue:
                self.ui_queue.put(
                    {"type": "refresh_memory_inspector", "turn_id": turn_id}
                )

        # Navigation
        if tool_name in ["move", "world.travel"] and isinstance(result, dict):
            loc_data = result.get("location_data", {})
            exits = list((loc_data.get("connections") or {}).keys())
            if self.ui_queue:
                self.ui_queue.put(
                    {"type": "update_nav", "exits": exits, "turn_id": turn_id}
                )
