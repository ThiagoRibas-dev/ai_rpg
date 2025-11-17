
import re


def _parse_duration(description: str) -> int:
    """A simple parser to estimate duration in hours from a text description."""
    description = description.lower()
    
    # Look for explicit numbers of hours/days
    hours_match = re.search(r'(\d+)\s*hour', description)
    if hours_match:
        return int(hours_match.group(1))
        
    days_match = re.search(r'(\d+)\s*day', description)
    if days_match:
        return int(days_match.group(1)) * 24

    # Check for keywords
    if "a week" in description:
        return 7 * 24
    if "overnight" in description or "until morning" in description or "until dawn" in description:
        return 8
    if "afternoon" in description:
        return 4
    
    return 0 # Default to no significant duration

def handler(description: str, new_time: str, **context: dict) -> dict:
    """
    Advance the game's fictional time.
    """
    session_id = context.get("session_id")
    db_manager = context.get("db_manager")

    if not session_id or not db_manager:
        raise ValueError("Missing session context")

    return {
        "old_time": context.get("current_game_time", "Unknown"),
        "new_time": new_time,
        "description": description,
        "duration_hours": _parse_duration(description), # NEW: Return estimated duration
    }
