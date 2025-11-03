from pydantic import BaseModel, Field
from typing import List, Dict, Any

class CharacterAttributes(BaseModel):
    hp_current: int
    hp_max: int
    # Other core stats (strength, dexterity, etc.) can be added here.

class Character(BaseModel):
    # --- CORE SCHEMA ---
    key: str = Field(..., description="Unique identifier, e.g., 'player'.")
    name: str = Field(..., description="The character's display name.")
    attributes: CharacterAttributes
    conditions: List[str] = Field(default_factory=list)
    location_key: str
    inventory_key: str

    # --- DYNAMIC EXTENSION ---
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Sandbox for AI-defined attributes like 'Sanity', 'Mana', 'Corruption'."
    )

class Item(BaseModel):
    key: str = Field(..., description="Unique identifier for the item.")
    name: str = Field(..., description="The item's display name.")
    description: str = Field(default="", description="A brief description of the item.")
    
    # --- DYNAMIC EXTENSION ---
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Sandbox for AI-defined item attributes like 'Durability', 'Enchantment', 'Weight'."
    )

class Location(BaseModel):
    key: str = Field(..., description="Unique identifier for the location.")
    name: str = Field(..., description="The location's display name.")
    description: str = Field(default="", description="A brief description of the location.")
    
    # --- DYNAMIC EXTENSION ---
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Sandbox for AI-defined location attributes like 'Weather', 'DangerLevel', 'SpecialEffect'."
    )
