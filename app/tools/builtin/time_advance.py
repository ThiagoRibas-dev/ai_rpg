schema = {
    "name": "time.advance",
    "description": "Advance the fictional game time. Use when narrative time passes (e.g., 'several hours later', 'the next morning').",
    "parameters": {
        "type": "object",
        "properties": {
            "description": {
                "type": "string",
                "description": "Human-readable time advancement, e.g., '3 hours', 'until dawn', 'to the next day'"
            },
            "new_time": {
                "type": "string", 
                "description": "The new fictional time, e.g., 'Day 2, Afternoon' or 'Hour 4 of the siege'"
            }
        },
        "required": ["description", "new_time"]
    }
}

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
        "description": description
    }