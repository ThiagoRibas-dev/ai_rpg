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
    dice_notation: str = Field(..., description="The standard dice formula used (e.g. '1d20', '3d6', 'd100').")
    roll_mechanic: str = Field(..., description="How to calculate the result (e.g. 'Roll + Mod vs DC', 'Roll under Skill', 'Count successes').")
    success_condition: str = Field(..., description="What determines success? (e.g. 'Result >= Target Number', 'At least 1 six').")
    crit_rules: str = Field(..., description="Rules for critical success/failure (e.g. 'Nat 20 / Nat 1').")


class ProcedureDef(BaseModel):
    """A specific game loop."""
    description: str = Field(..., description="A summary of what this procedure resolves.")
    steps: List[str] = Field(default_factory=list, description="Ordered list of steps to resolve this loop.")


class GameLoopConfig(BaseModel):
    """Procedures grouped by mode."""
    combat: Optional[ProcedureDef] = Field(None, description="Steps for resolving fights/initiative.")
    exploration: Optional[ProcedureDef] = Field(None, description="Steps for travel, perception, and environment.")
    social: Optional[ProcedureDef] = Field(None, description="Steps for persuasion, intimidation, and NPC interaction.")
    downtime: Optional[ProcedureDef] = Field(None, description="Steps for resting, crafting, or leveling up.")
    general_procedures: dict[str, ProcedureDef] = Field(default_factory=dict, description="Any other specific sub-systems (e.g. 'Hacking', 'Chase', 'Horror').")


class Ruleset(BaseModel):
    """Root Configuration."""
    meta: Dict[str, str] = Field(default_factory=lambda: {"name": "Untitled", "genre": "Generic"})
    
    physics: PhysicsConfig = Field(..., description="Core dice mechanics.")
    gameplay_loops: GameLoopConfig = Field(default_factory=GameLoopConfig, description="Structured procedures for game modes.")
    
    mechanics: dict[str, RuleEntry] = Field(
        default_factory=dict, 
        description="The Compendium. Map of Rule Name -> Rule Definition. Extract specific mechanics like 'Grapple', 'Falling', 'Conditions', 'Spells'."
    )
