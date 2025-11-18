from typing import Dict, Any
from app.setup.setup_manifest import SetupManifest

def handler(reason: str, **context: Any) -> Dict[str, Any]:
    """
    A simple flag tool that signals the end of the Session Zero setup phase.
    The orchestrator listens for this result to transition the game mode.

    Args:
        reason (str): The reason for starting the gameplay.
        context (Any): The tool execution context.

    Returns:
        Dict[str, Any]: A dictionary indicating that setup is complete.
    """
    session_id = context.get("session_id")
    db = context.get("db_manager")

    if not session_id or not db:
        return {"success": False, "error": "Missing session context."}

    manifest_mgr = SetupManifest(db)
    
    # Check if confirmation is pending
    if not manifest_mgr.is_pending_confirmation(session_id):
        return {
            "setup_complete": False,
            "error": "Prerequisite Failed: You must summarize the game state and use 'request_setup_confirmation' before starting the game. Do that now."
        }

    return {"setup_complete": True, "reason": reason}
