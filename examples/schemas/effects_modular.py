# effects_modular.py
from __future__ import annotations

from pydantic import Field
from typing import List, Optional, Union, Literal
from .base import SchemaModel

from .enums import (
    Stat,
    BonusType,
    EffectType,
    ProficiencyCategory,
    # Centralized enums (strict)
    Condition,
    EnergyType,
    HPChangeType,
    DRBypass,
    SenseType,
    MovementMode,
    TriggerEvent,
    RefreshCycle,
    AttackType,
    RollType,
    DRLogic,
    HealOverTimeMode,
    Maneuverability,
    CombatManeuver,
    AlignmentTag,
    AbilityShort,
    SpellSchool,
    SpellSubschool,
    AfflictionType,
)

# -----------------------------
# Core primitives (kept/updated)
# -----------------------------

class Dice(SchemaModel):
    """
    Represents a dice roll, e.g., 3d6.
    """
    quantity: int
    sides: int


class ScalingValue(SchemaModel):
    """
    Represents a value that scales based on a character attribute.
    """
    base_value: Union[int, float] = Field(..., description="Base value before scaling.")
    scaling_attribute: Optional[str] = Field(
        None,
        description="Attribute to scale with (e.g., 'caster_level', 'character_level', 'class_level:monk', 'wisdom_mod').",
    )
    multiplier: float = Field(1.0, description="Multiplier for the scaling attribute.")


class Cost(SchemaModel):
    """
    Represents a resource cost for activating an effect.
    """
    resource: str = Field(..., description="Resource to be spent (e.g., 'turn_undead_attempt', 'bardic_music_use').")
    amount: int = Field(..., description="Amount of the resource to be spent.")


class ModifierEffect(SchemaModel):
    """
    A generic effect that modifies (bonus, penalty) a specific character stat.
    """
    type: Literal[EffectType.MODIFIER] = EffectType.MODIFIER
    name: Optional[str] = None
    description: Optional[str] = None
    target: Stat
    value: Union[int, ScalingValue, bool]
    modifier_type: BonusType


# Unified HP change (damage/healing via energy semantics)
class HpChangeEffect(SchemaModel):
    """
    Changes hit points: handles physical damage, energy damage, and positive/negative energy healing rules.
    """
    type: Literal[EffectType.HP_CHANGE] = EffectType.HP_CHANGE
    amount: Union[int, Dice, ScalingValue]
    change_types: Optional[List[HPChangeType]] = Field(None, description="Types of Damage or Healing to apply. Slashing, Bluedgeoning, Acid, Fire, Positive Energy, etc. Healing is a special type for non-positive energy healing effects.")


class GrantFeatEffect(SchemaModel):
    """
    Effect that grants a character a feat.
    """
    type: Literal[EffectType.GRANT_FEAT] = EffectType.GRANT_FEAT
    feat_id: str = Field(..., description="Compendium ID of the feat to be granted.")


class BonusFeatEffect(SchemaModel):
    """
    Effect that grants a specific bonus feat (distinct from general feat choices).
    """
    type: Literal[EffectType.BONUS_FEAT] = EffectType.BONUS_FEAT
    feat_id: str = Field(..., description="Compendium ID of the bonus feat to be granted.")


class GrantProficiencyEffect(SchemaModel):
    """
    Grants proficiency in armor, weapons, or skills.
    Prefer this over bespoke familiarity models.
    """
    type: Literal[EffectType.GRANT_PROFICIENCY] = EffectType.GRANT_PROFICIENCY
    category: ProficiencyCategory = Field(..., description="Category (e.g., 'armor', 'weapon', 'skill').")
    proficiencies: List[str] = Field(..., description="List of compendium IDs to grant proficiency in.")


class GrantAbilityEffect(SchemaModel):
    """
    Grants a general ability or feature (descriptive or toggles).
    """
    type: Literal[EffectType.GRANT_ABILITY] = EffectType.GRANT_ABILITY
    name: str
    description: str
    daily_uses: Optional[int] = None
    value: Union[int, str, None] = None


class ManeuverProgressionEffect(SchemaModel):
    """
    Defines maneuver progression for martial adepts.
    """
    type: Literal[EffectType.MANEUVER_PROGRESSION] = EffectType.MANEUVER_PROGRESSION
    disciplines: Optional[List[str]] = None
    maneuvers_known: Optional[int] = None
    maneuvers_readied: Optional[int] = None
    maneuvers_granted: Optional[int] = None
    stances_known: Optional[int] = None


class GrantCohortEffect(SchemaModel):
    """
    Grants a cohort (e.g., animal companion, familiar, dragon cohort).
    """
    type: Literal[EffectType.GRANT_COHORT] = EffectType.GRANT_COHORT
    cohort_type: str
    ecl_modifier: int


class ImmunityEffect(SchemaModel):
    """
    Grants immunity to certain conditions/afflictions.
    Use ResistanceEffect for energy immunity; this type is not for energy.
    """
    type: Literal[EffectType.TEMPORARY_IMMUNITY] = EffectType.TEMPORARY_IMMUNITY
    condition: str = Field(..., description="Condition/affliction, e.g., 'poison', 'paralysis', 'fear'.")
    target: str = Field(..., description="Target scope (e.g., 'self').")


class MetamagicModification(SchemaModel):
    """
    Represents a modification applied by a metamagic feat.
    """
    target: str
    value: Union[str, int]


class MetamagicEffect(SchemaModel):
    """
    Represents a metamagic feat.
    """
    type: Literal[EffectType.METAMAGIC] = EffectType.METAMAGIC
    name: str
    spell_level_increase: int
    modifications: List[MetamagicModification]


class ActionOptionEffect(SchemaModel):
    """
    Grants a special action option (toggle/mode or activated ability).
    """
    type: Literal[EffectType.ACTION_OPTION] = EffectType.ACTION_OPTION
    option: str
    cost: Optional[Cost] = None
    target_spell_type: Optional[str] = None
    metamagic_feat: Optional[str] = None


class GrantStanceChoiceEffect(SchemaModel):
    """
    Grants a choice of martial stances.
    """
    type: Literal[EffectType.GRANT_STANCE_CHOICE] = EffectType.GRANT_STANCE_CHOICE
    martial_adept_level_calculation: Optional[str] = None


class UsageWithoutAdeptLevels(SchemaModel):
    """
    Details for using maneuvers without adept levels.
    """
    frequency: str
    initiator_level_calculation: str


class GrantManeuverChoiceEffect(SchemaModel):
    """
    Grants a choice of martial maneuvers.
    """
    type: Literal[EffectType.GRANT_MANEUVER_CHOICE] = EffectType.GRANT_MANEUVER_CHOICE
    adds_discipline_skill_as_class_skill: Optional[bool] = None
    usage_without_adept_levels: Optional[UsageWithoutAdeptLevels] = None
    becomes_maneuver_known_with_adept_levels: Optional[bool] = None
    recovery_rules: Optional[str] = None
    exchangeable: Optional[bool] = None


class GrantBonusFeatChoiceEffect(SchemaModel):
    """
    Grants a choice of bonus feats from a specific category.
    """
    type: Literal[EffectType.GRANT_BONUS_FEAT_CHOICE] = EffectType.GRANT_BONUS_FEAT_CHOICE
    category: str


class GrantChoiceEffect(SchemaModel):
    """
    Generic effect for granting a choice from a list of options.
    """
    type: Literal[EffectType.GRANT_CHOICE] = EffectType.GRANT_CHOICE
    choice_type: str = Field(..., description="Type of choice (e.g., 'feat', 'skill_trick', 'domain').")
    options: List[str] = Field(default_factory=list, description="Compendium IDs for options (e.g., feat IDs).")
    number_of_choices: int = Field(1, description="Number of selections allowed.")


class KeyValuePair(SchemaModel):
    key: str
    value: Union[str, int, bool, float]


class SpecialMechanic(SchemaModel):
    """
    For unique mechanics that aren't simple stats or abilities,
    like the Crusader's delayed damage pool.
    """
    name: str
    state: List[KeyValuePair] = Field(default_factory=list)


# -----------------------------
# New, strict, centralized primitives
# -----------------------------

class Trigger(SchemaModel):
    """
    Declarative trigger for an effect to activate or apply.
    """
    event: TriggerEvent = Field(..., description="Event that fires this trigger.")
    description: Optional[str] = Field(None, description="Optional detail for nuanced triggers.")
    once: Optional[bool] = Field(False, description="If true, trigger only once per activation window.")


class ConditionEffect(SchemaModel):
    """
    Applies or removes a SRD condition (blinded, shaken, etc.).
    """
    type: Literal[EffectType.CONDITION] = EffectType.CONDITION
    condition: Condition
    apply: bool = True


class DamageReductionEffect(SchemaModel):
    """
    DR X/TYPE with optional multiple bypass types and logic (any/all).
    """
    type: Literal[EffectType.DAMAGE_REDUCTION] = EffectType.DAMAGE_REDUCTION
    amount: Union[int, float]
    bypasses: List[DRBypass] = Field(default_factory=list, description="What bypasses the DR. Empty => DR X/—.")
    logic: DRLogic = DRLogic.ANY
    description: Optional[str] = None


class ResistEntry(SchemaModel):
    """
    Encodes resistance/immunity/vulnerability to one energy type.
    """
    energy: EnergyType
    amount: Optional[int] = Field(None, description="Resistance amount; omit if only immunity/vulnerability is used.")
    immunity: Optional[bool] = False
    vulnerability_multiplier: Optional[float] = Field(None, description="e.g., 1.5 for +50% damage")


class ResistanceEffect(SchemaModel):
    """
    Collects energy resistances, immunities, and vulnerabilities.
    """
    type: Literal[EffectType.RESISTANCE] = EffectType.RESISTANCE
    entries: List[ResistEntry] = Field(default_factory=list)


class HealingOverTimeEffect(SchemaModel):
    """
    Fast healing or regeneration over time.
    """
    type: Literal[EffectType.HEALING_OVER_TIME] = EffectType.HEALING_OVER_TIME
    mode: HealOverTimeMode
    rate: Union[int, float, ScalingValue]
    lethal_sources: Optional[List[str]] = Field(None, description="For regeneration: e.g., ['fire','acid','silver','good']")
    description: Optional[str] = None


class SenseEffect(SchemaModel):
    """
    Adds a special sense with a given range (where applicable).
    """
    type: Literal[EffectType.SENSE] = EffectType.SENSE
    sense: SenseType
    range: Optional[int] = Field(None, description="Feet. For Scent, leave None; rules adjust by wind/strength.")


class TargetFilter(SchemaModel):
    """
    Strict scoping/filtering for roll and weapon effects.
    """
    attack_types: Optional[List[AttackType]] = None
    combat_maneuvers: Optional[List[CombatManeuver]] = None
    weapon_groups: Optional[List[str]] = None     # compendium tags/ids
    weapon_ids: Optional[List[str]] = None        # compendium ids
    creature_types: Optional[List[str]] = None    # compendium ids/tags
    alignments: Optional[List[AlignmentTag]] = None


class RollModifierEffect(SchemaModel):
    """
    General roll bonus for attack or damage, with strict scoping via TargetFilter.
    """
    type: Literal[EffectType.ROLL_MODIFIER] = EffectType.ROLL_MODIFIER
    roll: RollType
    value: Union[int, float, ScalingValue, Dice]
    bonus_type: BonusType = BonusType.UNTYPED
    filter: Optional[TargetFilter] = None
    description: Optional[str] = None


class NegativeLevelEffect(SchemaModel):
    """
    Applies negative levels; engine handles save after 24 hours by default unless overridden.
    """
    type: Literal[EffectType.NEGATIVE_LEVEL] = EffectType.NEGATIVE_LEVEL
    count: int = 1
    save_dc: Optional[int] = Field(None, description="Override DC if needed; default is 10 + 1/2 attacker HD + Cha mod.")
    notes: Optional[str] = None


class AbilityDamageRoll(SchemaModel):
    """
    Encodes ability damage or drain.
    """
    ability: AbilityShort
    dice: Optional[Dice] = None
    flat: Optional[int] = None
    drain: bool = Field(False, description="True => ability drain instead of damage.")


class AbilityDamageEffect(SchemaModel):
    """
    Applies one or more ability damage/drain components.
    """
    type: Literal[EffectType.ABILITY_DAMAGE] = EffectType.ABILITY_DAMAGE
    rolls: List[AbilityDamageRoll] = Field(default_factory=list)


class ApplyAfflictionEffect(SchemaModel):
    """
    Applies a poison or disease by compendium id.
    """
    type: Literal[EffectType.AFFLICTION] = EffectType.AFFLICTION
    affliction_type: AfflictionType
    affliction_id: str
    save_dc_override: Optional[int] = None
    notes: Optional[str] = None


class SpellLikeAbilityEffect(SchemaModel):
    """
    Grants a spell-like ability with uses and caster level.
    """
    type: Literal[EffectType.SPELL_LIKE_ABILITY] = EffectType.SPELL_LIKE_ABILITY
    spell_id: str
    uses_per_day: Optional[int] = 1
    caster_level: Union[int, ScalingValue]
    save_dc_basis_ability: Optional[AbilityShort] = Field(None, description="If set, DC = 10 + spell level + this ability mod.")
    self_only: Optional[bool] = Field(False, description="If true, can only target self.")
    notes: Optional[str] = None


class ResourcePoolEffect(SchemaModel):
    """
    Defines a named resource pool (e.g., Turn Undead attempts).
    """
    type: Literal[EffectType.RESOURCE_POOL] = EffectType.RESOURCE_POOL
    resource_id: str = Field(..., description="Identifier, e.g., 'turn_undead_attempt'.")
    max_amount: Union[int, ScalingValue] = Field(..., description="Max capacity (e.g., 3 + Cha mod).")
    refresh: RefreshCycle = RefreshCycle.PER_DAY
    description: Optional[str] = None


class WeaponPropertyEffect(SchemaModel):
    """
    Grants properties and/or DR-bypass tags to certain attacks/weapons.
    """
    type: Literal[EffectType.WEAPON_PROPERTY] = EffectType.WEAPON_PROPERTY
    applies_to: Optional[TargetFilter] = None
    properties: List[str] = Field(default_factory=list, description="E.g., ['thundering','keen','flaming']")
    counts_as: List[DRBypass] = Field(default_factory=list, description="Treat as 'magic', 'lawful', 'adamantine', etc. for DR bypass.")
    description: Optional[str] = None


class GrantsMovementModeEffect(SchemaModel):
    """
    Grants a movement mode and speed (or sets it).
    """
    type: Literal[EffectType.MOVEMENT_MODE] = EffectType.MOVEMENT_MODE
    mode: MovementMode
    speed: int
    maneuverability: Optional[Maneuverability] = Field(None, description="For flying: clumsy/poor/average/good/perfect.")


class TemporaryHPEffect(SchemaModel):
    """
    Grants temporary HP with standard stacking semantics (non-stacking by default).
    """
    type: Literal[EffectType.TEMPORARY_HP] = EffectType.TEMPORARY_HP
    amount: Union[int, Dice]
    stacking: Optional[bool] = Field(False, description="If true, temp HP stacks with itself; usually false.")
    description: Optional[str] = None


class SpellSchoolFilter(SchemaModel):
    """
    School/subschool filter for spell-augmented effects.
    """
    school: SpellSchool
    subschool: Optional[SpellSubschool] = None


class SummoningAugmentEffect(SchemaModel):
    """
    Augments creatures you summon; default applies to conjuration (Summoning).
    """
    type: Literal[EffectType.SUMMONING_AUGMENT] = EffectType.SUMMONING_AUGMENT
    applies_when_casting: List[SpellSchoolFilter] = Field(
        default_factory=lambda: [SpellSchoolFilter(school=SpellSchool.CONJURATION, subschool=SpellSubschool.SUMMONING)]
    )
    modifiers: List[ModifierEffect] = Field(default_factory=list, description="Applied to summoned creatures for the duration.")