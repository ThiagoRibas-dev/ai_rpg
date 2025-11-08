
def handler(description: str, new_time: str, **context) -> dict:
    """
    Advance the game's fictional time.
    """
    session_id = context.get("session_id")
    db_manager = context.get("db_manager")

    if not session_id or not db_manager:
        raise ValueError("Missing session context")

    # Update the session's game time
    # Note: You'll need to add a method to update just the game_time field
    # For now, we'll return the info for the orchestrator to handle

    return {
        "old_time": context.get("current_game_time", "Unknown"),
        "new_time": new_time,
        "description": description,
    }
