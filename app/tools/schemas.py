from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field

JSONValue = Union[str, int, float, bool, dict, List]

# --- SUPER TOOLS ---

class EntityUpdate(BaseModel):
    name: Literal["entity.update"] = "entity.update"
    target_key: str = Field(..., description="Entity ID.")
    adjustments: Optional[Dict[str, int]] = None
    updates: Optional[Dict[str, Any]] = None
    inventory: Optional[Dict[str, Any]] = None

class GameRoll(BaseModel):
    name: Literal["game.roll"] = "game.roll"
    formula: str = Field(..., description="Dice string.")
    reason: str = Field(..., description="Context.")

class WorldTravel(BaseModel):
    name: Literal["world.travel"] = "world.travel"
    destination: str = Field(...)

class GameLog(BaseModel):
    name: Literal["game.log"] = "game.log"
    content: str = Field(...)
    category: Literal["event", "fact", "quest"] = "event"
    tags: Optional[List[str]] = None

class TimeAdvance(BaseModel):
    name: Literal["time.advance"] = "time.advance"
    description: str = Field(...)
    new_time: str = Field(...)

# --- WIZARD / SETUP TOOLS ---

class NpcSpawn(BaseModel):
    name: Literal["npc.spawn"] = "npc.spawn"
    key: str = Field(...)
    name_display: str = Field(...)
    visual_description: str = Field(...)
    stat_template: str = Field(...)
    initial_disposition: Literal["hostile", "neutral", "friendly"] = "neutral"
    location_key: Optional[str] = None

class LocationNeighbor(BaseModel):
    target_key: str
    direction: str

class LocationCreate(BaseModel):
    name: Literal["location.create"] = "location.create"
    key: str = Field(...)
    name_display: str = Field(...)
    description_visual: str = Field(...)
    description_sensory: str = Field(...)
    type: str = Field(...)
    # Optimization: Dict of neighbors (Direction -> Target Key/Data)
    # Actually, let's keep it simple for now as Dict[Direction, TargetKey]
    neighbors: dict[str, str] = Field(default_factory=dict, description="Map of Direction -> Target Key")

class MemoryUpsert(BaseModel):
    name: Literal["memory.upsert"] = "memory.upsert"
    kind: str = Field(...)
    content: str = Field(...)
    priority: int = 3
    tags: Optional[List[str]] = None

# --- UTILS ---

class MathEval(BaseModel):
    name: Literal["math.eval"] = "math.eval"
    expression: str = Field(...)

class StateQuery(BaseModel):
    name: Literal["state.query"] = "state.query"
    entity_type: str = Field(...)
    key: str = Field(...)
    json_path: str = Field(...)

class InventoryAddItem(BaseModel):
    name: Literal["inventory.add_item"] = "inventory.add_item"
    owner_key: str = Field(...)
    item_name: str = Field(...)
    quantity: int = 1
    description: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    target_slot: Optional[str] = None

class CharacterUpdate(BaseModel):
    name: Literal["character.update"] = "character.update"
    character_key: str = Field(...)
    updates: List[Any] = Field(...)

class Deliberate(BaseModel):
    name: Literal["deliberate"] = "deliberate"
