"""
Models for the Game System Rules.
Organized by Domain (Physics, Economy, Scripts).
"""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class RuleEntry(BaseModel):
    """Atomic rule for RAG."""
    name: str
    text: str
    tags: List[str] = Field(default_factory=list)


class PhysicsConfig(BaseModel):
    """The Resolution Engine."""
    dice_notation: str = Field(..., description="e.g. '1d20', '3d6'")
    roll_mechanic: str = Field(..., description="e.g. 'Roll + Mod vs DC', 'Roll under Skill'")
    success_condition: str = Field(..., description="e.g. 'Total >= Target'")
    crit_rules: str = Field("Nat 20 / Nat 1", description="Critical success/failure rules.")


class ProcedureDef(BaseModel):
    """A specific game loop."""
    name: str
    description: str
    steps: List[str] = Field(default_factory=list)


class GameLoopConfig(BaseModel):
    """Procedures grouped by mode."""
    combat: Optional[ProcedureDef] = None
    exploration: Optional[ProcedureDef] = None
    social: Optional[ProcedureDef] = None
    downtime: Optional[ProcedureDef] = None
    # TWEAK: Renamed for clarity
    general_procedures: List[ProcedureDef] = Field(default_factory=list)


class Ruleset(BaseModel):
    """Root Configuration."""
    meta: Dict[str, str] = Field(default_factory=lambda: {"name": "Untitled", "genre": "Generic"})
    
    physics: PhysicsConfig
    gameplay_loops: GameLoopConfig = Field(default_factory=GameLoopConfig)
    
    # Static Library (The Compendium)
    mechanics: List[RuleEntry] = Field(default_factory=list)
