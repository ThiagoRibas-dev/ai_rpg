"""
Models for the Generic Functional StatBlock.
Layout is now flattened: Stats directly declare their Panel and Group.
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
    HEADER = "header"       # Top bar (Name, Class)
    SIDEBAR = "sidebar"     # Left col (Attributes, Saves)
    MAIN = "main"           # Center (Combat, Actions)
    EQUIPMENT = "equipment" # Inventory
    SPELLS = "spells"       # Magic
    NOTES = "notes"         # Bio

# --- Data Primitives ---

class StatValue(BaseModel):
    id: str = Field(..., description="Unique key (e.g. 'str').")
    label: str = Field(..., description="Display name.")
    data_type: Literal["string", "integer", "boolean", "formula"] = "integer"
    default: Any = 0
    calculation: Optional[str] = None
    
    # Direct Layout Assignment
    widget: str = "number"
    panel: str = Field("main", description="Target Panel (header, sidebar, main, etc).")
    group: str = Field("General", description="Section header within the panel (e.g. 'Attributes').")

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
    values: Dict[str, StatValue] = Field(default_factory=dict)
    gauges: Dict[str, StatGauge] = Field(default_factory=dict)
    collections: Dict[str, StatCollection] = Field(default_factory=dict)
    # layout_groups is removed. Logic is distributed.
