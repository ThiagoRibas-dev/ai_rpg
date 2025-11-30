"""
Models for the Generic Functional StatBlock.
Refactored to separate Fundamental Inputs from Derived Outputs.
"""

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field

# --- UI Definitions ---


class WidgetType(str):
    TEXT_LINE = "text_line"  # Standard string input
    TEXT_AREA = "text_area"  # Bio/Notes
    NUMBER = "number"  # Standard integer input
    BONUS = "bonus"  # Number with + sign
    DIE = "die"  # Dropdown/Badge (d4, d6, d8...)
    LADDER = "ladder"  # Fate-style (Good [+3])
    CHECKBOX = "checkbox"  # Single boolean toggle
    BAR = "bar"  # Progress bar (HP)
    CLOCK = "clock"  # Segmented circle (4/6/8 segments)
    TRACK = "track"  # Series of checkboxes (Stress)


class PanelType(str):
    HEADER = "header"
    SIDEBAR = "sidebar"
    MAIN = "main"
    EQUIPMENT = "equipment"
    SPELLS = "spells"
    NOTES = "notes"


# --- Data Primitives ---
class StatRendering(BaseModel):
    """Visual hints for the UI."""

    icon: Optional[str] = None
    color_code: Optional[str] = None
    # For Enum/Ladder types: map value to display text (e.g., { "4": "Great" })
    lookup_map: Optional[Dict[str, str]] = None
    # For Tracks: labels for specific indices (e.g., ["", "", "Trauma"])
    labels: Optional[List[str]] = None


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


class StatTrack(BaseModel):
    """
    Resource with discreet states (Stress, Harm, Spell Slots).
    Unlike Gauges, these are usually 0-N integer counts, but rendered as boxes.
    """

    id: str = Field(..., description="Unique key (e.g. 'stress').")
    label: str = Field(..., description="Display name.")
    length: int = 5
    alias_zero: str = "Clear"
    alias_max: str = "Broken"

    widget: str = "track"
    panel: str = Field("main", description="Target Panel.")
    group: str = Field("Tracks", description="Section header.")
    rendering: Optional[StatRendering] = None


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

    # 5.  Discreet  States (Stress, Harm)
    tracks: Dict[str, StatTrack] = Field(default_factory=dict)
