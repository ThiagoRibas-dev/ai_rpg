import json
import logging
from typing import List, Dict, Any, Tuple

class ToolExecutor:
    """Executes tool calls, integrates with UI, and handles per-tool hooks like time.advance."""
    def __init__(self, tool_registry, db_manager, vector_store, ui=None, logger: logging.Logger | None = None):
        self.tools = tool_registry
        self.db = db_manager
        self.vs = vector_store
        self.ui = ui
        self.logger = logger or logging.getLogger(__name__)

    def execute(self, tool_calls, session, tool_budget: int, current_game_time: str | None = None) -> Tuple[List[Dict[str, Any]], bool]:
        results: List[Dict[str, Any]] = []
        memory_tool_used = False
        if not tool_calls:
            return results, memory_tool_used
        for call in tool_calls[:tool_budget]:
            tool_name = call.name
            try:
                tool_args = json.loads(call.arguments or "{}")
            except Exception:
                tool_args = {}
            if self.ui:
                try:
                    self.ui.add_tool_call(tool_name, tool_args)
                except Exception:
                    pass
            ctx = {
                "session_id": session.id,
                "db_manager": self.db,
                "vector_store": self.vs,
                "current_game_time": current_game_time,
            }
            try:
                result = self.tools.execute_tool(tool_name, tool_args, context=ctx)
                results.append({"tool_name": tool_name, "arguments": tool_args, "result": result})
                if self.ui:
                    try:
                        self.ui.add_tool_result(result, is_error=False)
                    except Exception:
                        pass
                # Hooks
                self._post_hook(tool_name, result, session)
                if tool_name in {"memory.upsert", "memory.update", "memory.delete", "memory.query"}:
                    memory_tool_used = True
            except Exception as e:
                self.logger.error(f"Error executing tool {tool_name}: {e}")
                results.append({"tool_name": tool_name, "arguments": tool_args, "error": str(e)})
                if self.ui:
                    try:
                        self.ui.add_tool_result(str(e), is_error=True)
                    except Exception:
                        pass
        return results, memory_tool_used

    def _post_hook(self, tool_name: str, result: Any, session):
        # time.advance -> persist and update UI
        if tool_name == "time.advance" and isinstance(result, dict) and "new_time" in result:
            try:
                self.db.update_session_game_time(session.id, result["new_time"])
                session.game_time = result["new_time"]
                if self.ui and hasattr(self.ui, "game_time_label"):
                    self.ui.game_time_label.configure(text=f"🕐 {result['new_time']}")
            except Exception as e:
                self.logger.error(f"Failed to update game time: {e}")
