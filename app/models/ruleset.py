"""
Models for the Game System Rules.
Optimized for Token Efficiency with Rich Descriptions.
"""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class RuleEntry(BaseModel):
    """Atomic rule for RAG."""
    text: str = Field(..., description="The concise text of this rule entry.")
    tags: List[str] = Field(default_factory=list, description="Keywords to find this rule entry (e.g. 'combat', 'stealth', 'magic').")


class PhysicsConfig(BaseModel):
    """The Resolution Engine."""
    dice_notation: str = Field(..., description="The standard formula used for dice rolls in this system (e.g. '1d20', '3d6', 'd100', etc).")
    roll_mechanic: str = Field(..., description="Instructions on how to resolve a roll using the dice notation (e.g. 'Roll + Mod vs DC', 'Roll under Skill', 'Count successes', etc).")
    success_condition: str = Field(..., description="The condition required to count a roll as a success (e.g. 'Result >= Target Number', 'At least 1 six', etc).")
    crit_rules: str = Field(..., description="Rules describing what happens on a critical success or failure(e.g. 'Nat 20 / Nat 1', '10 over / 10 under DC', etc).")


class ProcedureDef(BaseModel):
    """A specific game loop."""
    description: str = Field(..., description="A summary of the conflict or activity this procedure resolves.")
    steps: List[str] = Field(default_factory=list, description="The sequential list of actions required to complete this procedure.")


class GameLoopConfig(BaseModel):
    """Procedures grouped by mode."""
    combat: Optional[ProcedureDef] = Field(None, description="The procedure for resolving combat encounters.")
    exploration: Optional[ProcedureDef] = Field(None, description="The procedure for navigating the environment.")
    social: Optional[ProcedureDef] = Field(None, description="The procedure for influencing NPCs.")
    downtime: Optional[ProcedureDef] = Field(None, description="The procedure for resting and recovery.")
    general_procedures: dict[str, ProcedureDef] = Field(default_factory=dict, description="A dictionary of other specific subsystems found in the rules .")


class Ruleset(BaseModel):
    """Root Configuration."""
    meta: Dict[str, str] = Field(default_factory=lambda: {"name": "Untitled", "genre": "Generic"})
    
    physics: PhysicsConfig = Field(..., description="The core engine rules for dice and resolution.")
    gameplay_loops: GameLoopConfig = Field(default_factory=GameLoopConfig, description="The structured procedures for handling different game modes.")
    
    mechanics: dict[str, RuleEntry] = Field(
        default_factory=dict, 
        description="The dictionary of specific rule entries found in the text (The Compendium)."
    )
