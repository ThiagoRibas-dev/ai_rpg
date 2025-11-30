"""
Models for the Game System Rules.
Optimized for Token Efficiency with Rich Descriptions.
"""

from typing import List, Dict
from pydantic import BaseModel, Field


class RuleEntry(BaseModel):
    """Atomic rule for RAG."""
    text: str = Field(..., description="The concise text of this rule entry.")
    tags: List[str] = Field(
        default_factory=list,
        description="Keywords to find this rule entry (e.g. 'combat', 'stealth', 'magic', 'hacking', 'madness', etc).",
    )


class PhysicsConfig(BaseModel):
    """The Resolution Engine."""
    dice_notation: str = Field(
        ...,
        description="The standard formula used for dice rolls in this system (e.g. '1d20', '3d6', 'd100', etc).",
    )
    roll_mechanic: str = Field(
        ...,
        description="Instructions on how to resolve a roll using the dice notation (e.g. 'Roll + Mod vs DC', 'Roll under Skill', 'Count successes', etc).",
    )
    success_condition: str = Field(
        ...,
        description="The condition required to count a roll as a success (e.g. 'Result >= Target Number', 'At least 1 six', etc).",
    )
    crit_rules: str = Field(
        ...,
        description="Rules describing what happens on a critical success or failure(e.g. 'Nat 20 / Nat 1', '10 over / 10 under DC', etc).",
    )


class ProcedureDef(BaseModel):
    """A specific game loop."""
    description: str = Field(
        ...,
        description="A summary of the conflict or activity this procedure resolves.",
    )
    steps: List[str] = Field(
        default_factory=list,
        description="The sequential list of actions required to complete this procedure.",
    )


class GameLoopConfig(BaseModel):
    """Procedures grouped by mode. Each category can hold multiple specific procedures."""

    encounter: dict[str, ProcedureDef] = Field(
        default_factory=dict,
        description="Step-by-step procedures for resolving encounters (Standard Combat, Duels, Chases, Netrunning).",
    )

    exploration: dict[str, ProcedureDef] = Field(
        default_factory=dict,
        description="Step-by-step procedures for navigating the environment (Dungeon Crawl, Hex Travel, Investigation).",
    )

    social: dict[str, ProcedureDef] = Field(
        default_factory=dict,
        description="Step-by-step procedures for influencing NPCs (Persuasion, Intimidation, Bartering, Interrogation).",
    )

    downtime: dict[str, ProcedureDef] = Field(
        default_factory=dict,
        description="Step-by-step procedures for resting and recovery (Camping, Crafting, Training, Level Up).",
    )

    misc: dict[str, ProcedureDef] = Field(
        default_factory=dict,
        description="Other specific procedures found in the rules that don't fit above.",
    )


class Ruleset(BaseModel):
    """Root Configuration."""

    meta: Dict[str, str] = Field(
        default_factory=lambda: {"name": "Untitled", "genre": "Generic"}
    )

    physics: PhysicsConfig = Field(
        ..., description="The core engine rules for dice and resolution."
    )

    rules: dict[str, RuleEntry] = Field(
        default_factory=dict,
        description="The dictionary of specific rule entries.",
    )

    gameplay_procedures: GameLoopConfig = Field(
        default_factory=GameLoopConfig,
        description="The structured procedures for handling different game modes.",
    )
