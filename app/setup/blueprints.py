from typing import List, Literal
from pydantic import BaseModel, Field

class BlueprintField(BaseModel):
    """
    A simplified field definition for the LLM to generate.
    It flattens the complexity of Atoms/Molecules/Lists into high-level 'Concepts'.
    """
    key: str = Field(..., description="Snake_case key (e.g. 'str', 'hit_points').")
    label: str = Field(..., description="Display label (e.g. 'Strength', 'HP').")
    
    # The 'Concept' abstracts the structural complexity.
    # 'pool' implies a Molecule with Current/Max.
    # 'stat' implies an Atom with a Number.
    concept: Literal[
        "stat",         # Number (Atom)
        "text",         # String (Atom)
        "die",          # Dice code (Atom)
        "pool",         # Current/Max (Molecule)
        "track",        # Checkboxes (Molecule)
        "list",         # User-addable rows (Repeater)
        "toggle"        # Boolean (Atom)
    ] = Field(..., description="The semantic type of data.")

    # Hints for the Python Converter to build the full spec
    min_val: int = 0
    max_val: int = 20
    default_val: str = "0" # String representation to handle both text and numbers
    
    # For Lists only: The LLM defines simple columns here.
    # The Python converter will expand these into full SheetFields later.
    list_columns: List[str] = Field(
        default_factory=list, 
        description="If concept is 'list', define columns here (e.g. ['name', 'qty', 'weight'])."
    )

class CategoryBlueprint(BaseModel):
    fields: List[BlueprintField] = Field(default_factory=list)

class SheetBlueprint(BaseModel):
    """
    The Flat Structure for Generation.
    This mirrors the 10 Semantic Categories of the UCST, but uses the simple BlueprintField.
    """
    meta: CategoryBlueprint
    identity: CategoryBlueprint
    attributes: CategoryBlueprint
    skills: CategoryBlueprint
    resources: CategoryBlueprint
    features: CategoryBlueprint
    inventory: CategoryBlueprint
    connections: CategoryBlueprint
    narrative: CategoryBlueprint
    progression: CategoryBlueprint