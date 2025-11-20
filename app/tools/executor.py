import logging
import queue
from typing import Any, Dict, List, Tuple

from pydantic import BaseModel

from app.tools.schemas import (
    TimeAdvance,
    MemoryQuery,
    MemoryUpsert,
    MemoryUpdate,
    MemoryDelete,
    RngRoll,
    CharacterUpdate,
    InventoryAddItem,
    InventoryRemoveItem,
    StateApplyPatch
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
            tool_calls: List of validated Pydantic tool instances (e.g., [MathEval(...), MemoryUpsert(...)])
            session: The current game session
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

        # Define tools that are "safe" and don't invalidate the setup summary
        # SAFE_SETUP_TOOLS = [
        #     RequestSetupConfirmation.model_fields["name"].default,
        #     EndSetupAndStartGameplay.model_fields["name"].default,
        #     Deliberate.model_fields["name"].default,
        #     SchemaQuery.model_fields["name"].default,
        #     StateQuery.model_fields["name"].default,
        #     MemoryQuery.model_fields["name"].default,
        #     TimeNow.model_fields["name"].default,
        # ]

        for i, call in enumerate(tool_calls[:tool_budget]):
            # Debug logging to see what we actually got
            call_type = type(call)
            self.logger.debug(
                f"Tool call {i}: type={call_type.__name__}, is BaseModel={call_type is BaseModel}"
            )

            # Defensive check: ensure it's not a raw BaseModel
            if call_type is BaseModel or not hasattr(call, "name"):
                self.logger.error(
                    f"Invalid tool call at index {i}: {call_type} - {call}"
                )
                results.append(
                    {
                        "name": "unknown",
                        "arguments": {},
                        "error": f"Invalid tool call type: {call_type.__name__}",
                    }
                )
                continue

            # Safe access to name with fallback
            try:
                tool_name = call.name
            except AttributeError as e:
                self.logger.error(
                    f"Tool call has no 'name' attribute: {call_type} - {e}"
                )
                results.append(
                    {
                        "name": "unknown",
                        "arguments": {},
                        "error": f"Tool call missing 'name' field: {call_type.__name__}",
                    }
                )
                continue

            try:
                tool_args = call.model_dump(exclude={"name", "description"})
            except Exception as e:
                self.logger.error(f"Failed to dump model for {tool_name}: {e}")
                results.append(
                    {
                        "name": tool_name,
                        "arguments": {},
                        "error": f"Failed to serialize tool arguments: {e}",
                    }
                )
                continue

            # Validation is now delegated to individual tool handlers (e.g. character.update)
            # StateApplyPatch is considered a low-level "superuser" tool without schema validation.

            # Notify UI of tool call
            if self.ui_queue:
                try:
                    # Invalidation Logic for Setup Mode
                    # if getattr(session, "game_mode", "") == "SETUP":
                    #     try:
                    #         tool_name_str = getattr(call, "name", "")
                    #         if tool_name_str not in SAFE_SETUP_TOOLS:
                    #             manifest_mgr = SetupManifest(self.db)
                    #             if manifest_mgr.is_pending_confirmation(session.id):
                    #                 manifest_mgr.clear_pending_confirmation(session.id)
                    #                 self.logger.info(
                    #                     f"Tool {tool_name_str} invalidated pending setup confirmation."
                    #                 )
                    #     except Exception as e:
                    #         self.logger.warning(
                    #             f"Failed to run setup invalidation check: {e}"
                    #         )

                    self.logger.debug(f"Sending tool_call to UI queue: {tool_name}")
                    self.ui_queue.put(
                        {"type": "tool_call", "name": tool_name, "args": tool_args}
                    )
                except Exception as e:
                    self.logger.error(f"Failed to put tool_call on UI queue: {e}")

            try:
                # Execute using type-based dispatch
                result = self.tools.execute(call, context=ctx)
 
                # SPECIAL HANDLING: Dice Roll Visualization
                # We emit a specific event for the UI to render a dice bubble
                if isinstance(call, RngRoll) and self.ui_queue:
                    try:
                        self.ui_queue.put({
                            "type": "dice_roll",
                            "spec": tool_args.get("dice") or tool_args.get("dice_spec"),
                            "rolls": result.get("rolls", []),
                            "modifier": result.get("modifier", 0),
                            "total": result.get("total", 0)
                        })
                    except Exception as e:
                        self.logger.error(f"Failed to emit dice_roll event: {e}")

                results.append(
                    {"name": tool_name, "arguments": tool_args, "result": result}
                )

                # Notify UI of success
                if self.ui_queue:
                    try:
                        self.ui_queue.put(
                            {"type": "tool_result", "result": result, "is_error": False}
                        )
                    except Exception as e:
                        self.logger.error(f"Failed to put tool_result on UI queue: {e}")

                # Execute post-execution hooks
                self._post_hook(tool_name, result, session)

                # Type-based check for memory tools (more Pythonic than string check)
                if isinstance(
                    call,
                    (
                        MemoryUpsert,
                        MemoryQuery,
                        MemoryUpdate,
                        MemoryDelete,
                    ),
                ):
                    memory_tool_used = True

            except Exception as e:
                self.logger.error(
                    f"Error executing tool {tool_name}: {e}", exc_info=True
                )

                results.append(
                    {"name": tool_name, "arguments": tool_args, "error": str(e)}
                )

                # Notify UI of error
                if self.ui_queue:
                    try:
                        self.ui_queue.put(
                            {"type": "tool_result", "result": str(e), "is_error": True}
                        )
                    except Exception as e_ui:
                        self.logger.error(
                            f"Failed to put error tool_result on UI queue: {e_ui}"
                        )

        return results, memory_tool_used

    def _post_hook(self, tool_name: str, result: Any, session):
        """
        Execute post-execution hooks for specific tools.
        Currently handles time.advance to update session state.
        """
        # Special handling for time.advance
        if (
            tool_name == TimeAdvance.model_fields["name"].default
            and isinstance(result, dict)
            and "new_time" in result
        ):
            if not session:
                self.logger.warning(
                    "Session is None in _post_hook for time.advance. Cannot update game time."
                )
                return

            try:
                self.db.sessions.update_game_time(session.id, result["new_time"])
                session.game_time = result["new_time"]

                if self.ui_queue:
                    self.ui_queue.put(
                        {"type": "update_game_time", "new_time": result["new_time"]}
                    )
            except Exception as e:
                self.logger.error(f"Failed to update game time: {e}", exc_info=True)

        # Reactive UI Updates: Trigger Inspector Refreshes
        # Check against string names to avoid importing every single tool class if not needed,
        # though we imported some for the check.
        state_changing_tools = [
            CharacterUpdate.model_fields["name"].default,
            InventoryAddItem.model_fields["name"].default,
            InventoryRemoveItem.model_fields["name"].default,
            StateApplyPatch.model_fields["name"].default
        ]

        if tool_name in state_changing_tools and self.ui_queue:
            entity_type = "unknown"
            if tool_name == CharacterUpdate.model_fields["name"].default:
                entity_type = "character"
            elif "inventory" in tool_name:
                entity_type = "inventory"
            
            self.ui_queue.put({
                "type": "state_changed",
                "entity_type": entity_type
            })
