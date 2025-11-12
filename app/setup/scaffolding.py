# File: D:\Projects\Game Dev\ai-rpg\app\setup\scaffolding.py

# This file combines the original scaffolding_templates.py content
# and the genre detection/injection logic from SessionManager.

from typing import Dict, Any
from app.models.entities import Character, CharacterAttributes, Item, Location
# Assuming DBManager import for injection:
# from app.database.db_manager import DBManager 

def get_setup_scaffolding() -> Dict[str, Any]:
    """
    Returns the initial scaffolding structure for a new game in SETUP mode.
    ... (Rest of original get_setup_scaffolding content) ...
    """
    # Use Pydantic models for type safety
    player_character = Character(
        key="player",
        name="PLACEHOLDER",
        attributes=CharacterAttributes(hp_current=0, hp_max=0),
        conditions=[],
        location_key="starting_location",
        inventory_key="inventory:player",
        properties={
            "race": "PLACEHOLDER",
            "classes": ["PLACEHOLDER"],
            "level": 1,
        },
    )

    starting_item = Item(
        key="starter_item_01",
        name="PLACEHOLDER EQUIPMENT",
        description="PLACEHOLDER DESCRIPTION",
        properties={"quantity": 1, "equipped": False},
    )

    starting_location = Location(
        key="starting_location",
        name="PLACEHOLDER LOCATION",
        description="PLACEHOLDER DESCRIPTION",
        properties={},
    )

    # Serialize to dicts for database storage
    return {
        "character": {"player": player_character.model_dump()},
        "inventory": {
            "player": {
                "owner": "player",
                "items": [starting_item.model_dump()],
                "currency": {"gold": 0},
                "slots_used": 1,
                "slots_max": 10,
            }
        },
        "location": {"starting_location": starting_location.model_dump()},
    }


def get_genre_specific_scaffolding(genre: str) -> Dict[str, Any]:
    """
    Returns genre-specific scaffolding with suggested custom properties.
    ... (Rest of original get_genre_specific_scaffolding content) ...
    """
    base_scaffolding = get_setup_scaffolding()
    genre_suggestions = {
        # ... (genre_suggestions dict remains the same) ...
        "fantasy": {
            "character_properties": {"Mana": 50, "Faith": 100},
            "currency": {"gold": 10, "silver": 50},
        },
        "scifi": {
            "character_properties": {"Energy": 100, "Radiation": 0, "Cybernetics": 0},
            "currency": {"credits": 100},
        },
        "horror": {
            "character_properties": {"Sanity": 100, "Stress": 0, "Insight": 1},
            "currency": {"dollars": 50},
        },
        "cyberpunk": {
            "character_properties": {
                "Street_Cred": 0,
                "Heat": 0,
                "Augmentation_Slots": 3,
            },
            "currency": {"eddies": 200},
        },
    }

    if genre.lower() in genre_suggestions:
        suggestions = genre_suggestions[genre.lower()]
        if "character_properties" in suggestions:
            base_scaffolding["character"]["player"]["properties"].update(
                suggestions["character_properties"]
            )
        if "currency" in suggestions:
            base_scaffolding["inventory"]["player"]["currency"] = suggestions[
                "currency"
            ]

    return base_scaffolding


def detect_genre_from_prompt(prompt_content: str) -> str:
    """
    Simple heuristic to detect genre from prompt content.
    Returns 'generic' if no clear match.
    ... (Rest of original detect_genre_from_prompt content) ...
    """
    prompt_lower = prompt_content.lower()
    if any(word in prompt_lower for word in ["cyberpunk", "cyber", "netrunner", "chrome"]):
        return "cyberpunk"
    elif any(word in prompt_lower for word in ["horror", "lovecraft", "cosmic", "sanity", "terror"]):
        return "horror"
    elif any(word in prompt_lower for word in ["sci-fi", "scifi", "space", "starship", "alien"]):
        return "scifi"
    elif any(word in prompt_lower for word in ["fantasy", "magic", "dragon", "sword", "wizard"]):
        return "fantasy"
    else:
        return "generic"
        
# -----------------------------------------------
# NEWLY MOVED FUNCTIONALITY (from session_manager.py)
# -----------------------------------------------

def inject_setup_scaffolding(session_id: int, prompt_content: str, db_manager):
    """
    Inject initial scaffolding structure for SETUP mode.

    Args:
        session_id: Current session ID
        prompt_content: The prompt content (used for genre detection)
        db_manager: Database manager instance
    """
    genre = detect_genre_from_prompt(prompt_content)

    if genre != "generic":
        scaffolding = get_genre_specific_scaffolding(genre)
    else:
        scaffolding = get_setup_scaffolding()

    # Inject scaffolding into database
    for entity_type, entities in scaffolding.items():
        for entity_key, entity_data in entities.items():
            db_manager.set_game_state_entity(
                session_id, entity_type, entity_key, entity_data
            )
    
    # NOTE: Logging should be handled by the caller (SessionManager)
