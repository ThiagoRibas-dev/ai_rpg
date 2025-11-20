from typing import Any
from app.tools.builtin._state_storage import set_entity

def handler(
    key: str,
    name_display: str,
    description_visual: str,
    description_sensory: str,
    type: str,
    **context: Any
) -> dict:
    """
    Handler for location.create.
    Initializes a location entity with the correct structure and an empty connections dict.
    """
    session_id = context["session_id"]
    db = context["db_manager"]

    # Prevent overwrite of existing locations to be safe? 
    # Or allow update? Let's allow update/upsert for flexibility in Setup.
    
    location_data = {
        "name": name_display,
        "description_visual": description_visual,
        "description_sensory": description_sensory,
        "type": type,
        "connections": {} # Graph edges stored here
    }

    version = set_entity(session_id, db, "location", key, location_data)

    return {
        "success": True,
        "key": key,
        "name": name_display,
        "version": version
    }
