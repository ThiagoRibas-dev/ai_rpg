# File: app/tools/builtin/npc_adjust_relationship.py
# --- NEW FILE ---

from typing import List, Optional, Any
from app.tools.builtin._state_storage import get_entity, set_entity
from app.models.npc_profile import NpcProfile, RelationshipStatus


def handler(
    npc_key: str,
    subject_key: str,
    trust_change: Optional[int] = None,
    attraction_change: Optional[int] = None,
    fear_change: Optional[int] = None,
    tags_to_add: Optional[List[str]] = None,
    tags_to_remove: Optional[List[str]] = None,
    **context: Any,
) -> dict:
    """
    Handler for the npc.adjust_relationship tool.
    It loads an NPC's profile, modifies a relationship, and saves it back.
    """
    session_id = context.get("session_id")
    db = context.get("db_manager")

    if not session_id or not db:
        raise ValueError("Missing session context for npc.adjust_relationship.")

    # Load the profile, or create a default if it doesn't exist
    profile_data = get_entity(session_id, db, "npc_profile", npc_key)
    profile = NpcProfile(**profile_data) if profile_data else NpcProfile()

    # Get the specific relationship, or create a default
    relationship = profile.relationships.get(subject_key, RelationshipStatus())

    # Apply numerical changes and clamp values
    if trust_change is not None:
        relationship.trust = max(-10, min(10, relationship.trust + trust_change))
    if attraction_change is not None:
        relationship.attraction = max(-10, min(10, relationship.attraction + attraction_change))
    if fear_change is not None:
        relationship.fear = max(0, min(10, relationship.fear + fear_change))

    # Apply tag changes
    if tags_to_add:
        for tag in tags_to_add:
            if tag not in relationship.tags:
                relationship.tags.append(tag)
    if tags_to_remove:
        relationship.tags = [tag for tag in relationship.tags if tag not in tags_to_remove]

    # Update the profile and save it
    profile.relationships[subject_key] = relationship
    set_entity(session_id, db, "npc_profile", npc_key, profile.model_dump())

    return {
        "success": True,
        "npc_key": npc_key,
        "subject_key": subject_key,
        "new_status": relationship.model_dump(),
    }
