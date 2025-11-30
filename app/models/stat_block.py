"""
Models for the Generic Functional StatBlock.
Refactored to separate Fundamental Inputs from Derived Outputs.
"""

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field

# --- UI Definitions ---

class WidgetType(str):
    TEXT_LINE = "text_line"
    TEXT_AREA = "text_area"
    NUMBER = "number"
    BONUS = "bonus"
    DIE = "die"
    DOTS = "dots"
    CHECKBOX = "checkbox"
    BAR = "bar"
    CLOCK = "clock"
    FRACTION = "fraction"
    CHECK_GRID = "check_grid"

class PanelType(str):
    HEADER = "header"
    SIDEBAR = "sidebar"
    MAIN = "main"
    EQUIPMENT = "equipment"
    SPELLS = "spells"
    NOTES = "notes"

# --- Data Primitives ---

class StatValue(BaseModel):
    id: str = Field(..., description="Unique key (e.g. 'str').")
    label: str = Field(..., description="Display name.")
    data_type: Literal["string", "integer", "boolean", "formula"] = "integer"
    default: Any = 0
    calculation: Optional[str] = None
    
    # Layout
    widget: str = "number"
    panel: str = Field("main", description="Target Panel.")
    group: str = Field("General", description="Section header.")

class StatGauge(BaseModel):
    id: str = Field(..., description="Unique key (e.g. 'hp').")
    label: str = Field(..., description="Display name.")
    min_val: int = 0
    max_formula: str = "10"
    reset_on_rest: bool = True
    
    widget: str = "bar"
    panel: str = Field("main", description="Target Panel.")
    group: str = Field("Vitals", description="Section header.")

class CollectionItemField(BaseModel):
    key: str
    label: str
    data_type: Literal["string", "integer", "boolean"] = "string"
    widget: str = "text_line"

class StatCollection(BaseModel):
    id: str = Field(..., description="Unique key (e.g. 'inventory').")
    label: str = Field(..., description="Display name.")
    item_schema: List[CollectionItemField] = Field(default_factory=list)
    
    panel: str = Field("equipment", description="Target Panel.")
    group: str = Field("Items", description="Section header.")

# --- Root Template ---

class StatBlockTemplate(BaseModel):
    template_name: str
    
    # 1. Base Inputs (Str, Dex, Bio)
    fundamentals: Dict[str, StatValue] = Field(default_factory=dict)
    
    # 2. Lists (Inventory, Skills)
    collections: Dict[str, StatCollection] = Field(default_factory=dict)
    
    # 3. Calculated Outputs (AC, Save Bonuses)
    derived: Dict[str, StatValue] = Field(default_factory=dict)
    
    # 4. Resources (HP, Mana)
    gauges: Dict[str, StatGauge] = Field(default_factory=dict)
