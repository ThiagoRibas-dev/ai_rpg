import os

FILES = {}

# ==============================================================================
# 1. MODELS: STATBLOCK (Functional Descriptions)
# ==============================================================================
FILES["app/models/stat_block.py"] = """\"\"\"
Models for the Refined StatBlock Template.
Rich, functional descriptions embedded in fields to guide LLM extraction.
\"\"\"

from typing import List, Optional, Literal, Union, Dict
from pydantic import BaseModel, Field


class IdentityDef(BaseModel):
    \"\"\"Defines a category of identity.\"\"\"
    description: Optional[str] = Field(None, description="Explain what this identity category represents in the game world.")
    allow_multiple: bool = Field(False, description="Set to True if a character can hold multiple values for this category simultaneously.")
    value_type: Literal["selection", "text"] = Field("selection", description="Select 'selection' if the player chooses from a defined list, or 'text' if they write a freeform description.")


class FundamentalStatDef(BaseModel):
    \"\"\"The raw inputs for the system's math (Attributes).\"\"\"
    abbr: Optional[str] = Field(None, description="The standard abbreviation used for this stat.")
    description: Optional[str] = Field(None, description="Explain what aspect of the character this stat measures.")
    data_type: Literal["integer", "die_code", "dots", "float"] = Field("integer", description="The numerical format used to track this stat.")
    default: Union[int, str, float] = Field(10, description="The starting value assigned to an average character.")


class VitalResourceDef(BaseModel):
    \"\"\"Meters that determine life, death, or sanity.\"\"\"
    type: Literal["depleting", "accumulating"] = Field("depleting", description="Select 'depleting' if it counts down (like HP), or 'accumulating' if it counts up (like Stress).")
    min_value: int = 0
    max_formula: Optional[str] = Field(None, description="Formula to calculate the maximum capacity of this resource. Use '0' if static.")
    on_zero: Optional[str] = Field(None, description="The consequence applied when this resource reaches the minimum value.")
    on_max: Optional[str] = Field(None, description="The consequence applied when this resource reaches its maximum value.")


class ConsumableResourceDef(BaseModel):
    \"\"\"Fuel for abilities that refills over time.\"\"\"
    reset_trigger: str = Field("Rest", description="The event or condition that replenishes this resource.")
    max_formula: Optional[str] = Field(None, description="Formula to calculate the maximum capacity of this resource.")


class SkillDef(BaseModel):
    \"\"\"Learned proficiencies.\"\"\"
    linked_stat: Optional[str] = Field(None, description="The Fundamental Stat that modifies this skill.")
    can_be_untrained: bool = Field(True, description="Set to True if this skill can be used without specific training.")

SkillValue = Union[str, SkillDef]


class FeatureContainerDef(BaseModel):
    \"\"\"Buckets for special abilities (Feats, Spells, Edges).\"\"\"
    description: Optional[str] = Field(None, description="Explain what type of abilities or traits belong in this container.")


class EquipmentConfig(BaseModel):
    \"\"\"Inventory definition.\"\"\"
    capacity_stat: Optional[str] = Field(None, description="The stat or formula that determines how much a character can carry.")
    slots: dict[str, List[str]] = Field(
        default_factory=dict, 
        description="A dictionary mapping body slot names to the types of items they accept."
    )


class StatBlockTemplate(BaseModel):
    \"\"\"
    The blueprint for an Entity.
    Populate these dictionaries based on the Game Rules text.
    \"\"\"
    template_name: str = Field(..., description="The official name of this character sheet template.")
    
    identity_categories: dict[str, IdentityDef] = Field(
        default_factory=dict,
        description="The set of categorical traits that define a character's background (e.g. Race, Class)."
    )
    fundamental_stats: dict[str, FundamentalStatDef] = Field(
        default_factory=dict,
        description="The set of raw attributes that serve as inputs for game math (e.g. Strength, Agility)."
    )
    
    derived_stats: dict[str, str] = Field(
        default_factory=dict,
        description="The set of read-only values calculated from Fundamental Stats (e.g. AC, Initiative)."
    )
    
    vital_resources: dict[str, VitalResourceDef] = Field(
        default_factory=dict,
        description="The set of meters that determine character survival or sanity (e.g. HP, Stress)."
    )
    consumable_resources: dict[str, ConsumableResourceDef] = Field(
        default_factory=dict,
        description="The set of expendable resources used to power abilities (e.g. Mana, Ammo)."
    )
    
    skills: dict[str, SkillValue] = Field(
        default_factory=dict,
        description="The complete list of proficiencies available in the game."
    )
    features: dict[str, FeatureContainerDef] = Field(
        default_factory=dict,
        description="The categories of special abilities a character can acquire."
    )
    
    equipment: EquipmentConfig = Field(default_factory=EquipmentConfig)
"""

# ==============================================================================
# 2. MODELS: RULESET (Functional Descriptions)
# ==============================================================================
FILES["app/models/ruleset.py"] = """\"\"\"
Models for the Game System Rules.
Optimized for Token Efficiency with Rich Descriptions.
\"\"\"

from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class RuleEntry(BaseModel):
    \"\"\"Atomic rule for RAG.\"\"\"
    text: str = Field(..., description="The concise text of this rule entry.")
    tags: List[str] = Field(default_factory=list, description="Keywords to find this rule entry (e.g. 'combat', 'stealth', 'magic').")


class PhysicsConfig(BaseModel):
    \"\"\"The Resolution Engine.\"\"\"
    dice_notation: str = Field(..., description="The standard formula used for dice rolls in this system.")
    roll_mechanic: str = Field(..., description="Instructions on how to resolve a roll using the dice notation.")
    success_condition: str = Field(..., description="The condition required to count a roll as a success.")
    crit_rules: str = Field(..., description="Rules describing what happens on a critical success or failure.")


class ProcedureDef(BaseModel):
    \"\"\"A specific game loop.\"\"\"
    description: str = Field(..., description="A summary of the conflict or activity this procedure resolves.")
    steps: List[str] = Field(default_factory=list, description="The sequential list of actions required to complete this procedure.")


class GameLoopConfig(BaseModel):
    \"\"\"Procedures grouped by mode.\"\"\"
    combat: Optional[ProcedureDef] = Field(None, description="The procedure for resolving combat encounters.")
    exploration: Optional[ProcedureDef] = Field(None, description="The procedure for navigating the environment.")
    social: Optional[ProcedureDef] = Field(None, description="The procedure for influencing NPCs.")
    downtime: Optional[ProcedureDef] = Field(None, description="The procedure for resting and recovery.")
    general_procedures: dict[str, ProcedureDef] = Field(default_factory=dict, description="A dictionary of other specific subsystems found in the rules.")


class Ruleset(BaseModel):
    \"\"\"Root Configuration.\"\"\"
    meta: Dict[str, str] = Field(default_factory=lambda: {"name": "Untitled", "genre": "Generic"})
    
    physics: PhysicsConfig = Field(..., description="The core engine rules for dice and resolution.")
    gameplay_loops: GameLoopConfig = Field(default_factory=GameLoopConfig, description="The structured procedures for handling different game modes.")
    
    mechanics: dict[str, RuleEntry] = Field(
        default_factory=dict, 
        description="The dictionary of specific rule entries found in the text (The Compendium)."
    )
"""

def apply_refined_descriptions():
    print("ðŸ“   Applying Refined Functional Descriptions to Models...")
    for filepath, content in FILES.items():
        filepath = filepath.replace("/", os.sep)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        print(f"âœ ï¸   Updating {filepath}...")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    print("âœ… Done. Models now use directive descriptions.")

if __name__ == "__main__":
    apply_refined_descriptions()