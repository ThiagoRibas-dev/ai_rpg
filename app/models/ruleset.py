"""
Models for the Game System Rules.
Refactored: Flattened structure, 'Engine' instead of 'Physics', and Sheet Hints.
"""

from typing import List, Dict
from pydantic import BaseModel, Field


class EngineConfig(BaseModel):
    """The Resolution Engine (formerly Physics)."""

    dice_notation: str = Field(..., description="e.g. '1d20', '3d6', etc")
    roll_mechanic: str = Field(
        ..., description="e.g. 'Roll + Mod vs DC', 'Roll under Stat', etc"
    )
    success_condition: str = Field(
        ..., description="e.g. 'Result >= Target', 'Result <= Stat', etc"
    )
    crit_rules: str = Field(
        ..., description="e.g. 'Nat 20 is critical', '10 above target is critical', etc"
    )


class ProcedureDef(BaseModel):
    """A specific game loop."""

    description: str
    steps: List[str]


class Ruleset(BaseModel):
    """Root Configuration."""

    meta: Dict[str, str] = Field(
        default_factory=lambda: {"name": "Untitled", "genre": "Generic"}
    )

    engine: EngineConfig = Field(
        ..., description="The core mechanics of the game system."
    )

    # Flattened Procedures
    combat_procedures: Dict[str, ProcedureDef] = Field(
        default_factory=dict,
        description="Describes the steps for the different combat procedures.",
    )
    exploration_procedures: Dict[str, ProcedureDef] = Field(
        default_factory=dict,
        description="Describes the steps for the different exploration procedures.",
    )
    social_procedures: Dict[str, ProcedureDef] = Field(
        default_factory=dict,
        description="Describes the steps for the different social procedures.",
    )
    downtime_procedures: Dict[str, ProcedureDef] = Field(
        default_factory=dict,
        description="Describes the steps for the different downtime procedures.",
    )

    # Hints for the Sheet Generator
    sheet_hints: List[str] = Field(
        default_factory=list,
        description="Notes on stats/resources found in text (e.g. 'Uses Sanity', 'Has Strength').",
    )
