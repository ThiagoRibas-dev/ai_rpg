import logging
import queue
from typing import Any, Dict, List, Tuple

from pydantic import BaseModel

from app.tools.schemas import (
    EntityUpdate,
    GameLog,
    GameRoll,
    TimeAdvance,
    InventoryAddItem,
    MemoryUpsert,
)
from app.tools.schemas import WorldTravel


class ToolExecutor:
    """
    Executes tool calls from the LLM using type-based dispatch.
    Integrates with UI queue and handles per-tool hooks.
    Lifecycle-aware: attaches turn_id to all UI events.
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
        turn_id: str | None = None,  # New Argument
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Execute a list of tool calls from the LLM.
        """
        results: List[Dict[str, Any]] = []
        memory_tool_used = False

        if not tool_calls:
            self.logger.warning("No tool calls provided for execution.")
            return results, memory_tool_used

        # Build context once for all tools
        ctx = {
            "session_id": session.id,
            "db_manager": self.db,
            "vector_store": self.vs,
            "manifest": manifest,
            "current_game_time": current_game_time,
            "ui_queue": self.ui_queue,
        }

        if extra_context:
            ctx.update(extra_context)

        for i, call in enumerate(tool_calls[:tool_budget]):
            call_type = type(call)
            self.logger.debug(f"Tool call {i}: type={call_type.__name__}")

            if call_type is BaseModel or not hasattr(call, "name"):
                self.logger.error(f"Invalid tool call at index {i}: {call}")
                results.append({"name": "unknown", "error": "Invalid tool call type"})
                continue

            tool_name = call.name

            try:
                tool_args = call.model_dump(exclude={"name", "description"})
            except Exception as e:
                self.logger.error(f"Failed to dump model for {tool_name}: {e}")
                results.append(
                    {"name": tool_name, "error": f"Serialization failed: {e}"}
                )
                continue

            # Notify UI: Tool Call Started
            if self.ui_queue:
                try:
                    self.ui_queue.put(
                        {
                            "type": "tool_call",
                            "name": tool_name,
                            "args": tool_args,
                            "turn_id": turn_id,
                        }
                    )
                except Exception as e:
                    self.logger.error(f"Failed to put tool_call on UI queue: {e}")

            try:
                # --- EXECUTE TOOL ---
                result = self.tools.execute(call, context=ctx)

                # Visualization: Dice Roll (GameRoll)
                if isinstance(call, GameRoll) and self.ui_queue:
                    self.ui_queue.put(
                        {
                            "type": "dice_roll",
                            "spec": tool_args.get("formula"),
                            "rolls": result.get("rolls", []),
                            "modifier": 0,
                            "total": result.get("total", 0),
                            "turn_id": turn_id,
                        }
                    )

                results.append(
                    {"name": tool_name, "arguments": tool_args, "result": result}
                )

                # Notify UI: Tool Success
                if self.ui_queue:
                    self.ui_queue.put(
                        {
                            "type": "tool_result",
                            "result": result,
                            "is_error": False,
                            "turn_id": turn_id,
                        }
                    )

                # --- POST EXECUTION HOOKS ---
                self._post_hook(tool_name, result, session, turn_id)

                if isinstance(call, (GameLog, MemoryUpsert)):
                    memory_tool_used = True

            except Exception as e:
                self.logger.error(
                    f"Error executing tool {tool_name}: {e}", exc_info=True
                )
                results.append(
                    {"name": tool_name, "arguments": tool_args, "error": str(e)}
                )

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
        """
        Execute post-execution hooks for specific tools to update UI/Session state.
        """
        # 1. Time Advance: Update Session & UI Label
        if (
            tool_name == TimeAdvance.model_fields["name"].default
            and isinstance(result, dict)
            and "new_time" in result
        ):
            if session:
                try:
                    self.db.sessions.update_game_time(session.id, result["new_time"])
                    session.game_time = result["new_time"]
                    if self.ui_queue:
                        self.ui_queue.put(
                            {
                                "type": "update_game_time",
                                "new_time": result["new_time"],
                                "turn_id": turn_id,
                            }
                        )
                except Exception as e:
                    self.logger.error(f"Failed to update game time: {e}")

        # 2. State Changes: Trigger Inspector Refreshes
        if tool_name == EntityUpdate.model_fields["name"].default:
            if self.ui_queue:
                self.ui_queue.put(
                    {
                        "type": "state_changed",
                        "entity_type": "character",
                        "turn_id": turn_id,
                    }
                )
                self.ui_queue.put(
                    {
                        "type": "state_changed",
                        "entity_type": "inventory",
                        "turn_id": turn_id,
                    }
                )

        if tool_name in [
            InventoryAddItem.model_fields["name"].default,
        ]:
            if self.ui_queue:
                self.ui_queue.put(
                    {
                        "type": "state_changed",
                        "entity_type": "unknown",
                        "turn_id": turn_id,
                    }
                )

        # 3. Memory/Log Updates
        if tool_name in [
            GameLog.model_fields["name"].default,
            MemoryUpsert.model_fields["name"].default,
        ]:
            if self.ui_queue:
                self.ui_queue.put(
                    {"type": "refresh_memory_inspector", "turn_id": turn_id}
                )

        # 4. Navigation Updates
        if tool_name == WorldTravel.model_fields["name"].default and isinstance(
            result, dict
        ):
            loc = result.get("location_data") or {}
            conns = (loc.get("connections") or {}).keys()
            exits = list(conns)
            if self.ui_queue:
                self.ui_queue.put(
                    {"type": "update_nav", "exits": exits, "turn_id": turn_id}
                )
