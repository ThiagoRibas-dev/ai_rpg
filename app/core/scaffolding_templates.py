"""
Initial scaffolding templates for Session Zero (SETUP mode).

These provide a starting structure for the AI to populate and extend,
rather than creating everything from scratch.
"""
from typing import Dict, Any


def get_setup_scaffolding() -> Dict[str, Any]:
    """
    Returns the initial scaffolding structure for a new game in SETUP mode.
    
    This structure:
    - Provides placeholder entities for the AI to fill in
    - Demonstrates the expected schema format
    - Can be customized per genre/tone
    
    Returns:
        Dictionary of initial game state entities
    """
    return {
        "character": {
            "player": {
                "key": "player",
                "name": "[To be defined]",
                "race": "[To be defined]",
                "class": "[To be defined]",
                "level": 1,
                "attributes": {
                    "hp_current": 100,
                    "hp_max": 100
                },
                "conditions": [],
                "location": "starting_location",
                "inventory_key": "inventory:player",
                "properties": {
                    # Custom properties will be added here by schema.define_property
                    # Example: "Sanity": 100, "Mana": 50
                }
            }
        },
        "inventory": {
            "player": {
                "owner": "player",
                "items": [
                    # Example starting item (AI can modify/remove)
                    {
                        "id": "starter_item_01",
                        "name": "[Starting Equipment]",
                        "description": "Basic gear to get started",
                        "quantity": 1,
                        "equipped": False,
                        "properties": {}
                    }
                ],
                "currency": {
                    "gold": 0
                },
                "slots_used": 1,
                "slots_max": 10
            }
        },
        "location": {
            "starting_location": {
                "key": "starting_location",
                "name": "[Starting Location]",
                "description": "Where the adventure begins.",
                "properties": {
                    # Custom location properties
                    # Example: "DangerLevel": 1, "Weather": "Clear"
                }
            }
        }
    }


def get_genre_specific_scaffolding(genre: str) -> Dict[str, Any]:
    """
    Returns genre-specific scaffolding with suggested custom properties.
    
    This is OPTIONAL - the AI can ignore these suggestions if the player
    describes something different.
    
    Args:
        genre: Detected or specified genre (fantasy, scifi, horror, etc.)
    
    Returns:
        Scaffolding with genre-appropriate suggestions
    """
    base_scaffolding = get_setup_scaffolding()
    
    # Genre-specific property suggestions (these are just hints, not enforced)
    genre_suggestions = {
        "fantasy": {
            "character_properties": {
                "Mana": 50,
                "Faith": 100
            },
            "currency": {
                "gold": 10,
                "silver": 50
            }
        },
        "scifi": {
            "character_properties": {
                "Energy": 100,
                "Radiation": 0,
                "Cybernetics": 0
            },
            "currency": {
                "credits": 100
            }
        },
        "horror": {
            "character_properties": {
                "Sanity": 100,
                "Stress": 0,
                "Insight": 1
            },
            "currency": {
                "dollars": 50
            }
        },
        "cyberpunk": {
            "character_properties": {
                "Street_Cred": 0,
                "Heat": 0,
                "Augmentation_Slots": 3
            },
            "currency": {
                "eddies": 200
            }
        }
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
            base_scaffolding["inventory"]["player"]["currency"] = suggestions["currency"]
    
    return base_scaffolding


# Optional: Detect genre from prompt content
def detect_genre_from_prompt(prompt_content: str) -> str:
    """
    Simple heuristic to detect genre from prompt content.
    Returns 'generic' if no clear match.
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
