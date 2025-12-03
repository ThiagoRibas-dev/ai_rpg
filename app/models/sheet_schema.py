from typing import List, Dict, Optional, Literal, Any
from pydantic import BaseModel, Field

# --- Primitives ---


class FieldDisplay(BaseModel):
    """How to render the field"""

    widget: Literal[
        "text", "number", "pool", "track", "die", "toggle", "select", "repeater"
    ] = "text"
    label: str
    icon: Optional[str] = None
    hidden: bool = False
    options: Optional[List[Dict[str, Any]]] = None


class SheetField(BaseModel):
    """
    A Unified Field Definition.
    Combines Atom, Molecule, and List properties into one forgiving schema.
    """

    key: str

    # 1. Classification
    # Defaults to 'atom' so if the LLM forgets this key, it doesn't crash.
    container_type: Literal["atom", "molecule", "list"] = "atom"

    # 2. Data Properties (for Atoms)
    data_type: Literal["string", "number", "boolean", "derived"] = "string"
    default: Any = None
    formula: Optional[str] = None
    tags: List[str] = []

    # 3. Structural Properties (Recursive)
    # For Molecules (e.g. HP -> Current/Max)
    components: Optional[Dict[str, "SheetField"]] = None
    # For Lists (e.g. Inventory -> Item Schema)
    item_schema: Optional[Dict[str, "SheetField"]] = None

    # 4. UI
    display: FieldDisplay


# --- The 10 Categories ---


class SheetCategory(BaseModel):
    fields: Dict[str, SheetField] = Field(default_factory=dict)


class CharacterSheetSpec(BaseModel):
    """The Blueprint of the Character Sheet"""

    meta: SheetCategory = Field(default_factory=SheetCategory)
    identity: SheetCategory = Field(default_factory=SheetCategory)
    attributes: SheetCategory = Field(default_factory=SheetCategory)
    skills: SheetCategory = Field(default_factory=SheetCategory)
    resources: SheetCategory = Field(default_factory=SheetCategory)
    features: SheetCategory = Field(default_factory=SheetCategory)
    inventory: SheetCategory = Field(default_factory=SheetCategory)
    connections: SheetCategory = Field(default_factory=SheetCategory)
    narrative: SheetCategory = Field(default_factory=SheetCategory)
    progression: SheetCategory = Field(default_factory=SheetCategory)
