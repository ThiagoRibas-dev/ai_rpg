"""
Initial scaffolding templates for Session Zero (SETUP mode).

These provide a starting structure for the AI to populate and extend,
using validated Pydantic models to ensure correctness.
"""

from typing import Dict, Any
from app.models.entities import Character, CharacterAttributes, Item, Location


def get_setup_scaffolding() -> Dict[str, Any]:
    """
    Returns the initial scaffolding structure for a new game in SETUP mode.

    Uses Pydantic models to ensure schema validity.

    Returns:
        Dictionary of initial game state entities (as serialized dicts)
    """
    # ✅ Use Pydantic models for type safety
    player_character = Character(
        key="player",
        name="[To be defined]",
        attributes=CharacterAttributes(hp_current=0, hp_max=0),
        conditions=[],
        location_key="starting_location",
        inventory_key="inventory:player",
        properties={
            "race": "[To be defined]",
            "classes": ["[To be defined]"],  # Note: 'class' is a Python keyword
            "level": 1,
        },
    )

    starting_item = Item(
        key="starter_item_01",
        name="[Starting Equipment]",
        description="Basic gear to get started",
        properties={"quantity": 1, "equipped": False},
    )

    starting_location = Location(
        key="starting_location",
        name="[Starting Location]",
        description="Where the adventure begins.",
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

    Args:
        genre: Detected or specified genre (fantasy, scifi, horror, etc.)

    Returns:
        Scaffolding with genre-appropriate suggestions
    """
    # Start with base scaffolding
    base_scaffolding = get_setup_scaffolding()

    # Genre-specific property suggestions
    genre_suggestions = {
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

    # Apply genre suggestions if available
    if genre.lower() in genre_suggestions:
        suggestions = genre_suggestions[genre.lower()]

        # Merge character properties
        if "character_properties" in suggestions:
            base_scaffolding["character"]["player"]["properties"].update(
                suggestions["character_properties"]
            )

        # Update currency
        if "currency" in suggestions:
            base_scaffolding["inventory"]["player"]["currency"] = suggestions[
                "currency"
            ]

    return base_scaffolding


def detect_genre_from_prompt(prompt_content: str) -> str:
    """
    Simple heuristic to detect genre from prompt content.
    Returns 'generic' if no clear match.
    """
    prompt_lower = prompt_content.lower()

    if any(
        word in prompt_lower for word in ["cyberpunk", "cyber", "netrunner", "chrome"]
    ):
        return "cyberpunk"
    elif any(
        word in prompt_lower
        for word in ["horror", "lovecraft", "cosmic", "sanity", "terror"]
    ):
        return "horror"
    elif any(
        word in prompt_lower
        for word in ["sci-fi", "scifi", "space", "starship", "alien"]
    ):
        return "scifi"
    elif any(
        word in prompt_lower
        for word in ["fantasy", "magic", "dragon", "sword", "wizard"]
    ):
        return "fantasy"
    else:
        return "generic"
