"""
Models for the Game System Rules.
Refactored: Flattened structure, 'Engine' instead of 'Physics', and Sheet Hints.
"""

from typing import List, Dict, Optional
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



class StateInvariant(BaseModel):
    """
    A system-specific validation constraint extracted from the rules.
    Used to enforce game-specific bounds and constraints at runtime.
    """

    name: str = Field(..., description="Human-readable name for the constraint")
    target_path: str = Field(
        ...,
        description="Dot-path to the value being constrained, e.g., 'resources.hp.current'",
    )
    constraint: str = Field(
        ...,
        description="Comparison type: '>=', '<=', '==', 'in_range', 'is_one_of'",
    )
    reference: str = Field(
        ...,
        description="Literal value ('0', '100') or path to another field ('resources.hp.max')",
    )
    on_violation: str = Field(
        "clamp",
        description="Action on violation: 'clamp' (auto-correct), 'flag' (warn), 'reject' (fail)",
    )
    correction_value: Optional[str] = Field(
        None,
        description="Value to use when clamping - literal or path. If None, uses reference.",
    )


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

    state_invariants: List[StateInvariant] = Field(
        default_factory=list,
        description="Validation rules extracted from the game system, enforced on entity updates.",
    )

