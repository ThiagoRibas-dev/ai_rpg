import logging
import queue
from typing import Any, Dict, List, Tuple

from pydantic import BaseModel

from app.tools.schemas import (
    CharacterUpdate,
    InventoryAddItem,
    InventoryRemoveItem,
    MemoryDelete,
    MemoryQuery,
    MemoryUpdate,
    MemoryUpsert,
    RngRoll,
    TimeAdvance,
)


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
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Execute a list of tool calls from the LLM.

        Args:
            tool_calls: List of validated Pydantic tool instances
            session: The current game session
            manifest: Setup manifest dictionary
            tool_budget: Maximum number of tools to execute
            current_game_time: Optional fictional game time string

        Returns:
            Tuple of (results list, memory_tool_used flag)
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
        }

        for i, call in enumerate(tool_calls[:tool_budget]):
            # Debug logging
            call_type = type(call)
            self.logger.debug(f"Tool call {i}: type={call_type.__name__}")

            # Basic Validation
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
                        {"type": "tool_call", "name": tool_name, "args": tool_args}
                    )
                except Exception as e:
                    self.logger.error(f"Failed to put tool_call on UI queue: {e}")

            try:
                # --- EXECUTE TOOL ---
                result = self.tools.execute(call, context=ctx)

                # Visualization: Dice Roll
                if isinstance(call, RngRoll) and self.ui_queue:
                    self.ui_queue.put(
                        {
                            "type": "dice_roll",
                            "spec": tool_args.get("dice") or tool_args.get("dice_spec"),
                            "rolls": result.get("rolls", []),
                            "modifier": result.get("modifier", 0),
                            "total": result.get("total", 0),
                        }
                    )

                results.append(
                    {"name": tool_name, "arguments": tool_args, "result": result}
                )

                # Notify UI: Tool Success
                if self.ui_queue:
                    self.ui_queue.put(
                        {"type": "tool_result", "result": result, "is_error": False}
                    )

                # --- POST EXECUTION HOOKS ---
                self._post_hook(tool_name, result, session)

                # Track memory usage for return flag
                if isinstance(
                    call, (MemoryUpsert, MemoryQuery, MemoryUpdate, MemoryDelete)
                ):
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
                        {"type": "tool_result", "result": str(e), "is_error": True}
                    )

        return results, memory_tool_used

    def _post_hook(self, tool_name: str, result: Any, session):
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
                            {"type": "update_game_time", "new_time": result["new_time"]}
                        )
                except Exception as e:
                    self.logger.error(f"Failed to update game time: {e}")

        # 2. State Changes: Trigger Inspector Refreshes
        state_tools = [
            CharacterUpdate.model_fields["name"].default,
            InventoryAddItem.model_fields["name"].default,
            InventoryRemoveItem.model_fields["name"].default,
        ]

        if tool_name in state_tools and self.ui_queue:
            entity_type = "unknown"
            if tool_name == CharacterUpdate.model_fields["name"].default:
                entity_type = "character"
            elif "inventory" in tool_name:
                entity_type = "inventory"

            # RESTORED: Actually send the message to the queue
            self.ui_queue.put({"type": "state_changed", "entity_type": entity_type})

        # 3. Memory Updates: Refresh Memory Inspector
        memory_tools = [
            MemoryUpsert.model_fields["name"].default,
            MemoryUpdate.model_fields["name"].default,
            MemoryDelete.model_fields["name"].default,
        ]

        if tool_name in memory_tools and self.ui_queue:
            self.ui_queue.put({"type": "refresh_memory_inspector"})
