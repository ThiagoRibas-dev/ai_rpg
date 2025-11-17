import logging
import queue
import copy
from typing import List, Dict, Any, Tuple
from pydantic import BaseModel
from app.tools import schemas
from app.utils.state_validator import StateValidator, ValidationError
from app.tools.builtin._state_storage import get_entity


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

        # Initialize the validator for this turn
        try:
            validator = StateValidator(manifest)
        except ValueError:
            validator = None # Manifest might be empty in early setup

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

            # --- VALIDATION GATEKEEPER ---
            # If the tool is state-modifying, validate its effect *before* executing.
            if validator and isinstance(call, schemas.StateApplyPatch):
                try:
                    # 1. Load the current entity state
                    current_entity = get_entity(ctx["session_id"], self.db, call.entity_type, call.key)
                    # 2. Simulate the patch on a copy
                    simulated_entity = copy.deepcopy(current_entity)
                    # This is a simplified patch application for simulation.
                    # For a more robust solution, a jsonpatch library would be better.
                    for op in call.patch:
                        if op.op == "replace":
                            # Simplistic simulation for common cases
                            path_parts = op.path.strip('/').split('/')
                            temp = simulated_entity
                            for part in path_parts[:-1]:
                                temp = temp.setdefault(part, {})
                            temp[path_parts[-1]] = op.value
                    
                    # 3. Validate the simulated result
                    validator.validate_entity(call.entity_type, simulated_entity)
                    self.logger.debug(f"Pre-execution validation PASSED for {tool_name}")

                except ValidationError as e:
                    self.logger.warning(f"Validation FAILED for {tool_name}: {e}")
                    results.append({"name": tool_name, "arguments": tool_args, "error": f"Validation Error: {e}"})
                    continue # Skip execution of this invalid tool call

            # Notify UI of tool call
            if self.ui_queue:
                try:
                    self.logger.debug(f"Sending tool_call to UI queue: {tool_name}")
                    self.ui_queue.put(
                        {"type": "tool_call", "name": tool_name, "args": tool_args}
                    )
                except Exception as e:
                    self.logger.error(f"Failed to put tool_call on UI queue: {e}")

            try:
                # Execute using type-based dispatch
                result = self.tools.execute(call, context=ctx)

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
                        schemas.MemoryUpsert,
                        schemas.MemoryQuery,
                        schemas.MemoryUpdate,
                        schemas.MemoryDelete,
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
            tool_name == schemas.TimeAdvance.model_fields["name"].default
            and isinstance(result, dict)
            and "new_time" in result
        ):
            if not session:
                self.logger.warning("Session is None in _post_hook for time.advance. Cannot update game time.")
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
