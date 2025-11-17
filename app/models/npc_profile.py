# File: app/models/npc_profile.py
# --- NEW FILE ---

from pydantic import BaseModel, Field
from typing import List, Dict


class RelationshipStatus(BaseModel):
    """
    A structured model to quantify the relationship between two entities.
    """
    trust: int = Field(0, description="How much this NPC trusts the subject. Ranges from -10 (hated enemy) to 10 (unbreakable bond).")
    attraction: int = Field(0, description="Romantic or platonic attraction/liking. Ranges from -10 (disgusted) to 10 (infatuated).")
    fear: int = Field(0, description="How much this NPC fears the subject. Ranges from 0 (not at all) to 10 (terrified).")
    tags: List[str] = Field(
        default_factory=list,
        description="Descriptive tags for the relationship, e.g., ['rival', 'mentor', 'business associate', 'unrequited_love']."
    )


class NpcProfile(BaseModel):
    """
    An entity that stores the 'mind' of an NPC—their personality, goals, and
    relationships. This is separate from their physical 'character' stats.
    """
    personality_traits: List[str] = Field(
        default_factory=list,
        description="Core personality traits, e.g., ['brave', 'greedy', 'cautious', 'arrogant']."
    )
    motivations: List[str] = Field(
        default_factory=list,
        description="The NPC's primary goals or driving forces, e.g., ['Avenge my family', 'Acquire wealth', 'Protect the village']."
    )
    directive: str = Field(
        "idle",
        description="A simple, actionable goal for the NPC to pursue when off-screen, e.g., 'patrol the town walls', 'gather herbs in the woods'."
    )
    knowledge_tags: List[str] = Field(
        default_factory=list,
        description="A list of tags linking to 'lore' memories that this NPC knows."
    )
    relationships: Dict[str, RelationshipStatus] = Field(
        default_factory=dict,
        description="A dictionary mapping other entity keys (e.g., 'player') to their relationship status."
    )
