from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field

# A reusable JSON type
JSONValue = Union[str, int, float, bool, dict, List]

# --- SUPER TOOLS (ReAct Engine) ---

class EntityUpdate(BaseModel):
    """
    Update an entity's state (Character, NPC, Object).
    - adjustments: Relative math (e.g. {'hp': -5, 'gold': +10})
    - updates: Absolute sets (e.g. {'status': 'Prone', 'disposition': 'Hostile'})
    - inventory: Manage items (e.g. {'add': {'name': 'Key', 'qty': 1}})
    """
    name: Literal["entity.update"] = "entity.update"
    target_key: str = Field(..., description="Entity ID (e.g., 'player', 'goblin_1').")
    adjustments: Optional[Dict[str, int]] = Field(None, description="Math changes. e.g. {'hp': -5}.")
    updates: Optional[Dict[str, Any]] = Field(None, description="Absolute sets. e.g. {'status': 'Prone'}.")
    inventory: Optional[Dict[str, Any]] = Field(None, description="Inventory changes. e.g. {'add': {'name': 'Sword'}}.")

class GameRoll(BaseModel):
    """
    Roll dice for a check, attack, or save.
    """
    name: Literal["game.roll"] = "game.roll"
    formula: str = Field(..., description="Dice string (e.g., '1d20+5').")
    reason: str = Field(..., description="Context for the roll (e.g., 'Attack vs Goblin AC').")

class WorldTravel(BaseModel):
    """
    Move the party to a different location.
    """
    name: Literal["world.travel"] = "world.travel"
    destination: str = Field(..., description="Target Location Key (e.g., 'tavern_common_room').")

class GameLog(BaseModel):
    """
    Record a memory, quest update, or important fact.
    """
    name: Literal["game.log"] = "game.log"
    content: str = Field(..., description="The fact or event to remember.")
    category: Literal["event", "fact", "quest"] = Field("event", description="Type of log.")
    tags: Optional[List[str]] = Field(None, description="Search tags.")

class TimeAdvance(BaseModel):
    """
    Advance fictional game time (triggers world simulation).
    """
    name: Literal["time.advance"] = "time.advance"
    description: str = Field(..., description="Narrative description (e.g. 'You sleep for 8 hours').")
    new_time: str = Field(..., description="The new time string.")

# --- WIZARD / SETUP TOOLS (Keep for SetupWizard) ---

class NpcSpawn(BaseModel):
    name: Literal["npc.spawn"] = "npc.spawn"
    key: str = Field(..., description="Unique ID.")
    name_display: str = Field(..., description="Name shown to player.")
    visual_description: str = Field(..., description="Physical appearance.")
    stat_template: str = Field(..., description="Template name (e.g. 'Commoner').")
    initial_disposition: Literal["hostile", "neutral", "friendly"] = Field("neutral")
    location_key: Optional[str] = Field(None)

class LocationCreate(BaseModel):
    name: Literal["location.create"] = "location.create"
    key: str = Field(..., description="Unique ID.")
    name_display: str = Field(..., description="Display name.")
    description_visual: str = Field(..., description="Visuals.")
    description_sensory: str = Field(..., description="Smell, sound.")
    type: str = Field(..., description="Environment type.")
    neighbors: List[Dict[str, str]] = Field(default_factory=list)

class MemoryUpsert(BaseModel):
    """Legacy wrapper for Wizard lore generation."""
    name: Literal["memory.upsert"] = "memory.upsert"
    kind: str = Field(...)
    content: str = Field(...)
    priority: int = 3
    tags: Optional[List[str]] = None

# --- UTILS ---

class MathEval(BaseModel):
    name: Literal["math.eval"] = "math.eval"
    expression: str = Field(..., description="Math expression.")

class StateQuery(BaseModel):
    name: Literal["state.query"] = "state.query"
    entity_type: str = Field(...)
    key: str = Field(...)
    json_path: str = Field(...)

class InventoryAddItem(BaseModel):
    """Kept for Wizard compatibility if needed."""
    name: Literal["inventory.add_item"] = "inventory.add_item"
    owner_key: str = Field(...)
    item_name: str = Field(...)
    quantity: int = 1
    description: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None

class CharacterUpdate(BaseModel):
    """Kept for Wizard compatibility."""
    name: Literal["character.update"] = "character.update"
    character_key: str = Field(...)
    updates: List[Any] = Field(...)

class Deliberate(BaseModel):
    name: Literal["deliberate"] = "deliberate"
