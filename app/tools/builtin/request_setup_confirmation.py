from typing import Dict, Any
from app.setup.setup_manifest import SetupManifest

def handler(summary: str, **context: Any) -> Dict[str, Any]:
    """
    Sets the session state to 'confirmation_pending'.
    """
    session_id = context.get("session_id")
    db = context.get("db_manager")

    if not session_id or not db:
        return {"success": False, "error": "Missing session context."}

    manifest_mgr = SetupManifest(db)
    manifest_mgr.set_pending_confirmation(session_id, summary)

    return {
        "success": True, 
        "status": "waiting_for_user_confirmation",
        "message": "Summary recorded. Ask the user to confirm if they are ready to play."
    }
