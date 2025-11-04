# effects.py
from __future__ import annotations

from typing import List, Optional, Union
from pydantic import Field

from app.schemas.effects_modular import (
    # Common/shared
    Trigger,
    # Core effect payloads (import only those you allow in each wrapper)
    ModifierEffect,
    RollModifierEffect,
    HpChangeEffect,
    TemporaryHPEffect,
    DamageReductionEffect,
    ResistanceEffect,
    HealingOverTimeEffect,
    SenseEffect,
    GrantsMovementModeEffect,
    ConditionEffect,
    ImmunityEffect,
    GrantProficiencyEffect,
    GrantAbilityEffect,
    GrantFeatEffect,
    GrantChoiceEffect,
    ResourcePoolEffect,
    ActionOptionEffect,
    SpellLikeAbilityEffect,
    WeaponPropertyEffect,
    SummoningAugmentEffect,
    AbilityDamageEffect,
)

from .enums import (
    DurationType,
    ConditionalType,
    ComparisonKey,
    ComparisonOp,
)
from .base import SchemaModel


# Domain-specific unions

# Races: typical racial traits (bonuses, senses, movement, resistances, proficiencies, SLAs, occasional bonus feat)
RaceEffectDetails = Union[
    ModifierEffect,
    RollModifierEffect,
    ResistanceEffect,
    DamageReductionEffect,
    SenseEffect,
    GrantsMovementModeEffect,
    GrantProficiencyEffect,
    GrantAbilityEffect,
    GrantFeatEffect,
    GrantChoiceEffect,
    ImmunityEffect,
    SpellLikeAbilityEffect,
]

# Classes: features, resources, toggles, ToB chassis, senses, movement, SLAs, healing over time
ClassEffectDetails = Union[
    ModifierEffect,
    RollModifierEffect,
    ResourcePoolEffect,
    ActionOptionEffect,
    SpellLikeAbilityEffect,
    HealingOverTimeEffect,
    SenseEffect,
    GrantsMovementModeEffect,
    ImmunityEffect,
    GrantAbilityEffect,
    GrantProficiencyEffect,
    GrantFeatEffect,
    GrantChoiceEffect,
    SummoningAugmentEffect,
]

# Feats: numeric modifiers, roll modifiers, toggles, resources, resistances, SLAs, augmentations
FeatEffectDetails = Union[
    ModifierEffect,
    RollModifierEffect,
    ResourcePoolEffect,
    ActionOptionEffect,
    ResistanceEffect,
    ImmunityEffect,
    SpellLikeAbilityEffect,
    SummoningAugmentEffect,
    GrantAbilityEffect,
    GrantProficiencyEffect,
    GrantFeatEffect,
    GrantChoiceEffect,
]

# Items: weapon properties, buffs, resistances/DR, HP change (potions, life stealing), SLAs, toggles
ItemEffectDetails = Union[
    WeaponPropertyEffect,
    ModifierEffect,
    RollModifierEffect,
    ResistanceEffect,
    DamageReductionEffect,
    TemporaryHPEffect,
    HpChangeEffect,
    SpellLikeAbilityEffect,
    ActionOptionEffect,
    ResourcePoolEffect,
    ImmunityEffect,
    SenseEffect,
    GrantsMovementModeEffect,
]

# Spells: direct HP change, conditions, DR/resist, temp HP, (de)buffs, ability damage/drain
SpellEffectDetails = Union[
    HpChangeEffect,
    ConditionEffect,
    DamageReductionEffect,
    ResistanceEffect,
    TemporaryHPEffect,
    ModifierEffect,
    RollModifierEffect,
    AbilityDamageEffect,
]

# Psionic powers: mirror spells (adjust if you model psionics differently)
PowerEffectDetails = Union[
    HpChangeEffect,
    ConditionEffect,
    DamageReductionEffect,
    ResistanceEffect,
    TemporaryHPEffect,
    ModifierEffect,
    RollModifierEffect,
    AbilityDamageEffect,
]

class Conditional(SchemaModel):
    """
    Context/gating conditions and numeric comparisons.
    """
    type: Optional[ConditionalType] = None
    target: Optional[str] = None

    key: Optional[ComparisonKey] = None
    op: Optional[ComparisonOp] = None
    value: Optional[Union[str, int, float, bool]] = None
    rhs_key: Optional[ComparisonKey] = None


class EffectEnvelope(SchemaModel):
    """
    Shared envelope for all domain-specific effects.
    """
    details: object = Field(..., description="Domain-specific effect payload.")
    duration_type: DurationType = DurationType.PERMANENT
    duration: Optional[Duration] = None
    conditionals: Optional[List[Conditional]] = None
    triggers: Optional[List[Trigger]] = None
    
# Wrapper models (plain Unions – emits anyOf, not discriminator/oneOf)
class RaceEffect(EffectEnvelope):
    details: RaceEffectDetails


class ClassEffect(EffectEnvelope):
    details: ClassEffectDetails


class FeatEffect(EffectEnvelope):
    details: FeatEffectDetails


class ItemEffect(EffectEnvelope):
    details: ItemEffectDetails


class SpellEffect(EffectEnvelope):
    details: SpellEffectDetails


class PowerEffect(EffectEnvelope):
    details: PowerEffectDetails

# Common envelope used by all wrappers
class Duration(SchemaModel):
    base: int
    ability_modifier: Optional[str] = None