import logging
from typing import Any
from app.tools.executor import ToolExecutor
from app.tools.schemas import Set
from app.setup.setup_manifest import SetupManifest
from app.database.db_manager import DBManager

logger = logging.getLogger(__name__)


class ManualEditService:
    """
    Service for manual (user-initiated) state edits.
    Bypasses the LLM but uses the ToolExecutor + ValidationPipeline.
    """

    def __init__(self, db_manager: DBManager, tool_registry, vector_store):
        self.db = db_manager
        self.tool_registry = tool_registry
        self.vector_store = vector_store

    def update_field(
        self,
        session_id: int,
        entity_type: str,
        entity_key: str,
        path: str,
        new_value: Any,
    ) -> dict:
        """
        Updates a single field on an entity.

        Args:
            session_id: The game session ID.
            entity_type: e.g., "character", "location".
            entity_key: e.g., "player", "npc_goblin".
            path: The dot-notation path to the field, e.g., "resources.hp.current".
            new_value: The new value to set.

        Returns:
            A dict with "success" and optional "message" or "error".
        """
        game_session = self.db.sessions.get_by_id(session_id)
        if not game_session:
            return {"success": False, "error": "Session not found."}

        # Build the full path including entity prefix
        full_path = f"{entity_type}.{entity_key}.{path}"

        # Construct the Set tool payload
        set_tool = Set(
            path=full_path,
            value=new_value,
        )

        # Get Manifest for validation context
        setup_data = SetupManifest(self.db).get_manifest(session_id)
        manifest_id = setup_data.get("manifest_id")
        manifest = self.db.manifests.get_by_id(manifest_id) if manifest_id else None

        # Execute via ToolExecutor (this triggers ValidationPipeline)
        executor = ToolExecutor(
            self.tool_registry,
            self.db,
            self.vector_store,
            ui_queue=None,  # No UI queue for manual edits
            logger=logger,
        )

        try:
            results, _ = executor.execute(
                tool_calls=[set_tool],
                session=game_session,
                manifest=setup_data,
                tool_budget=1,
                current_game_time=game_session.game_time,
                extra_context={"manifest": manifest, "source": "manual_edit"},
                turn_id="manual",
            )

            logger.debug(f"Manual edit attempt: {full_path} = {new_value}")
            logger.debug(f"Tool results: {results}")

            # Check if the tool executed successfully
            # The Set tool returns: {path, old_value, new_value, corrections, reason}
            # If there's an 'error' key, it failed
            if results:
                res = results[0]
                result_data = res.get("result", {})
                
                # Check for explicit error
                if res.get("error") or result_data.get("error"):
                    error = res.get("error") or result_data.get("error")
                    logger.warning(f"Manual edit failed for {full_path}: {error}")
                    return {"success": False, "error": error}
                
                # Success case: result has 'new_value' key (Set tool output)
                if "new_value" in result_data:
                    logger.info(f"Manual edit success: {full_path} = {result_data.get('new_value')}")
                    return {"success": True, "message": f"Updated {path}"}
                
                # Fallback: check for 'status' == 'ok'
                if result_data.get("status") == "ok":
                    logger.info(f"Manual edit success: {full_path} = {new_value}")
                    return {"success": True, "message": f"Updated {path}"}
            
            # If we get here, something unexpected happened
            logger.warning(f"Manual edit failed for {full_path}: Unexpected result format")
            logger.warning(f"Full result: {results}")
            return {"success": False, "error": "Unexpected result format"}

        except Exception as e:
            logger.error(f"Manual edit exception for {full_path}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
