from typing import List, Optional, Dict, Literal
from pydantic import Field

from .base import SchemaModel
from .effects import ClassEffect
from .effects_modular import SpecialMechanic
from .compendium_schemas import SpellsPerDay
from .enums import AbilityShort, SizeCategory
from .compendium_schemas import CompendiumCategory


# -----------------------------
# Core hit points and action points
# -----------------------------

class HitPoints(SchemaModel):
    base: int = Field(0, description="HP from class, level, and Constitution.")
    temporary: int = Field(0, description="Temporary HP from spells or effects.")
    current: int = Field(0, description="Current HP, cannot exceed base + temporary.")
    nonlethal: int = Field(0, description="Amount of nonlethal damage taken.")


class ActionPoints(SchemaModel):
    base: int = Field(0, description="Base action points.")
    temporary: int = Field(0, description="Temporary action points from spells or effects.")
    current: int = Field(0, description="Current action points.")


# -----------------------------
# Armor Class
# -----------------------------

class ArmorClassModifiers(SchemaModel):
    dexterity: int = Field(0, description="Dexterity modifier to AC.")
    armor: int = Field(0, description="Bonus from worn armor.")
    shield: int = Field(0, description="Bonus from shield.")
    natural: int = Field(0, description="Natural armor bonus.")
    deflection: int = Field(0, description="Deflection bonus to AC.")
    dodge: int = Field(0, description="Dodge bonus to AC.")
    size: int = Field(0, description="Size modifier to AC.")
    misc: int = Field(0, description="Miscellaneous AC modifiers (luck, sacred, profane, etc).")


class PlayerArmorClass(SchemaModel):
    total: int = Field(10, description="Total Armor Class.")
    base: int = Field(10, description="Base AC (10 + modifiers).")
    touch: int = Field(10, description="Touch AC (no armor or natural armor).")
    flat_footed: int = Field(10, description="Flat-footed AC (no Dex or dodge).")
    modifiers: ArmorClassModifiers = Field(default_factory=lambda: ArmorClassModifiers(), description="Detailed breakdown of AC modifiers.")


# -----------------------------
# BAB / Initiative / DR
# -----------------------------

class BaseAttackBonus(SchemaModel):
    base: int = Field(0)
    temporary: int = Field(0)
    current: int = Field(0)
    total: int = Field(0, description="The calculated total BAB (base + temporary).")


class Initiative(SchemaModel):
    base: int = Field(0, description="Base initiative from Dex mod and feats.")
    temporary: int = Field(0, description="Temporary initiative bonus from spells/effects.")
    total: int = Field(0, description="Calculated total initiative (base + temporary).")


class DamageReduction(SchemaModel):
    amount: int = Field(0, description="The amount of damage reduction.")
    bypass: Optional[str] = Field(None, description="Type that bypasses the reduction (e.g., 'magic', 'adamantine').")


class ReachProfile(SchemaModel):
    space_ft: int = Field(5, description="Occupied space in feet (default 5 for Medium).")
    natural_reach_ft: int = Field(5, description="Natural reach in feet (default 5 for Medium).")


class CombatStats(SchemaModel):
    base_attack_bonus: BaseAttackBonus = Field(default_factory=lambda: BaseAttackBonus(), description="The character's Base Attack Bonus progression.")
    initiative: Initiative = Field(default_factory=lambda: Initiative(), description="The character's initiative score.")
    grapple: int = Field(0, description="The character's grapple check modifier.")
    spell_resistance: int = Field(0, description="The character's spell resistance value.")
    damage_reduction: Optional[DamageReduction] = Field(None, description="Damage Reduction (e.g., '5/magic').")
    armor_check_penalty: int = Field(0, description="Penalty applied to certain skill checks when wearing armor.")
    size_category: SizeCategory = Field(SizeCategory.MEDIUM, description="Base size category.")
    reach: ReachProfile = Field(default_factory=lambda: ReachProfile(), description="Base space/reach; reach weapons and feats apply elsewhere.")


# -----------------------------
# Abilities & Saves
# -----------------------------

class CharacterAbility(SchemaModel):
    base: int = Field(10, description="The base ability score.")
    temporary: int = Field(0, description="Temporary adjustments to the ability score.")
    equipment: int = Field(0, description="Bonus from equipment to the ability score.")
    current: int = Field(10, description="The current effective score (base + temporary + equipment).")
    modifier: int = Field(0, description="Modifier derived from the current score.")


class PlayerAbilityScores(SchemaModel):
    strength: CharacterAbility = Field(default_factory=lambda: CharacterAbility(), description="Strength.")
    dexterity: CharacterAbility = Field(default_factory=lambda: CharacterAbility(), description="Dexterity.")
    constitution: CharacterAbility = Field(default_factory=lambda: CharacterAbility(), description="Constitution.")
    intelligence: CharacterAbility = Field(default_factory=lambda: CharacterAbility(), description="Intelligence.")
    wisdom: CharacterAbility = Field(default_factory=lambda: CharacterAbility(), description="Wisdom.")
    charisma: CharacterAbility = Field(default_factory=lambda: CharacterAbility(), description="Charisma.")


class CharacterSavingThrow(SchemaModel):
    base: int = Field(0, description="Base save bonus from classes.")
    temporary: int = Field(0, description="Temporary bonuses from effects.")
    total: int = Field(0, description="Calculated total save bonus (base + ability + temporary).")


class PlayerSavingThrows(SchemaModel):
    fortitude: CharacterSavingThrow = Field(default_factory=lambda: CharacterSavingThrow(), description="Fortitude save.")
    reflex: CharacterSavingThrow = Field(default_factory=lambda: CharacterSavingThrow(), description="Reflex save.")
    will: CharacterSavingThrow = Field(default_factory=lambda: CharacterSavingThrow(), description="Will save.")


# -----------------------------
# Movement
# -----------------------------

class MovementModeEntry(SchemaModel):
    mode: str = Field("", description="Mode (e.g., 'fly', 'swim').")
    speed: int = Field(0, description="Speed in feet for the mode.")


class Movement(SchemaModel):
    base: int = Field(30, description="Base land speed in feet.")
    current: int = Field(30, description="Current land speed.")
    units: str = Field("ft", description="Units (e.g., 'ft').")
    modes: List[MovementModeEntry] = Field(default_factory=list, description="Additional movement modes.")


# -----------------------------
# Spellcasting (per class)
# -----------------------------

class PerClassCasting(SchemaModel):
    class_id: str = Field(..., description="Casting class ID, e.g., 'cleric', 'wizard'.")
    casting_model: Literal["prepared", "spontaneous"] = Field(..., description="Prepared or spontaneous casting.")
    ability_score: AbilityShort = Field(..., description="Spellcasting ability (int, wis, cha).")
    caster_level: int = Field(0, description="Effective caster level for this class.")
    slots_per_day: SpellsPerDay = Field(default_factory=lambda: SpellsPerDay(), description="Slots per day by spell level (0–9).")
    spells_known_by_level: Optional[Dict[int, List[str]]] = Field(None, description="For spontaneous casters: known spells by level.")
    prepared_by_level: Optional[Dict[int, List[str]]] = Field(None, description="For prepared casters: prepared spells by level.")
    domains: Optional[List[str]] = Field(None, description="Cleric domains (if applicable).")
    domain_slots_per_day: Optional[SpellsPerDay] = Field(None, description="Domain slots per day (cleric).")


# -----------------------------
# Maneuvers (ToB)
# -----------------------------

class Maneuvers(SchemaModel):
    initiator_level: int = Field(0, description="Initiator level for maneuvers.")
    prepared: List[str] = Field(default_factory=list, description="Maneuvers prepared.")
    known: List[str] = Field(default_factory=list, description="Maneuvers known.")
    stances_known: List[str] = Field(default_factory=list, description="Martial stances known.")


# -----------------------------
# Inventory and equipment
# -----------------------------

class Coins(SchemaModel):
    cp: int = Field(0, description="Copper pieces.")
    sp: int = Field(0, description="Silver pieces.")
    gp: int = Field(0, description="Gold pieces.")
    pp: int = Field(0, description="Platinum pieces.")


class EquipmentSlots(SchemaModel):
    hand1: Optional[str] = Field(None, description="Item ID in main hand.")
    hand2: Optional[str] = Field(None, description="Item ID in off hand.")
    armor: Optional[str] = Field(None, description="Item ID of worn armor.")
    torso: Optional[str] = Field(None, description="Item ID worn on torso.")
    head: Optional[str] = Field(None, description="Item ID worn on head.")
    eyes: Optional[str] = Field(None, description="Item ID worn over eyes.")
    shoulders: Optional[str] = Field(None, description="Item ID worn on shoulders.")
    neck: Optional[str] = Field(None, description="Item ID worn around neck.")
    waist: Optional[str] = Field(None, description="Item ID worn around waist.")
    arms: Optional[str] = Field(None, description="Item ID worn on arms.")
    hands: Optional[str] = Field(None, description="Item ID worn on hands.")
    ring1: Optional[str] = Field(None, description="Item ID on first ring finger.")
    ring2: Optional[str] = Field(None, description="Item ID on second ring finger.")
    feet: Optional[str] = Field(None, description="Item ID worn on feet.")


class Inventory(SchemaModel):
    coins: Coins = Field(default_factory=lambda: Coins(), description="Currency.")
    gems: List[str] = Field(default_factory=list, description="Gem item IDs.")
    equipment: EquipmentSlots = Field(default_factory=lambda: EquipmentSlots(), description="Equipped items.")
    other_item_ids: List[str] = Field(default_factory=list, description="Other carried item IDs.")


# -----------------------------
# Class progression and content deps
# -----------------------------

class ClassProgressionEntry(SchemaModel):
    class_id: str = Field(..., description="The ID of the class.")
    level: int = Field(..., description="The level gained in that class.")


class ContentDependency(SchemaModel):
    name: str = Field(..., description="Name of the content item, e.g., 'Monk' or 'Weapon Focus'.")
    slug: str = Field(..., description="Slug for the content item.")
    category: CompendiumCategory = Field(..., description="Category, e.g., 'classes', 'races', 'feats'.")
    exists_in_compendium: bool = Field(False, description="True if this item already exists in the compendium.")


# -----------------------------
# Skills and attacks
# -----------------------------

class SkillEntry(SchemaModel):
    name: str = Field("", description="Skill name.")
    ranks: int = Field(0, description="Skill ranks invested.")
    modifier: int = Field(0, description="Total skill modifier.")
    trained_only: Optional[bool] = Field(None, description="If True, cannot be used untrained.")
    armor_check_penalty_applies: Optional[bool] = Field(None, description="If True, ACP applies.")


class Attack(SchemaModel):
    name: str = Field("", description="Attack name (e.g., 'Longsword', 'Claw').")
    bonus: int = Field(0, description="Total attack bonus.")
    damage: str = Field("", description="Damage roll (e.g., '1d8+4').")
    crit_range: str = Field("", description="Critical threat range (e.g., '19-20/x2').")
    type: str = Field("", description="Damage type (e.g., 'Slashing', 'Piercing').")


# -----------------------------
# Character sheet aggregates
# -----------------------------

class CharacterVitals(SchemaModel):
    name: str = Field("", description="Character's name.")
    alignment: str = Field("", description="Alignment (e.g., 'Lawful Good').")
    age: int = Field(0, description="Age in years.")
    deity: str = Field("", description="Deity or philosophy.")
    origin: str = Field("", description="Background or place of origin.")
    race_id: str = Field("", description="Race ID.")
    template_ids: List[str] = Field(default_factory=list, description="Template IDs applied.")
    languages: List[str] = Field(default_factory=list, description="Languages known.")
    misc_notes: Optional[str] = Field(None, description="Additional notes.")


class CharacterCombatStats(SchemaModel):
    hit_points: HitPoints = Field(default_factory=lambda: HitPoints(), description="Hit points.")
    action_points: ActionPoints = Field(default_factory=lambda: ActionPoints(), description="Action points.")
    armor_class: PlayerArmorClass = Field(default_factory=lambda: PlayerArmorClass(), description="Armor Class details.")
    combat: CombatStats = Field(default_factory=lambda: CombatStats(), description="Combat stats.")
    attacks: List[Attack] = Field(default_factory=list, description="Attack forms.")
    movement: Movement = Field(default_factory=lambda: Movement(), description="Movement speeds.")


class CharacterAbilities(SchemaModel):
    abilities: PlayerAbilityScores = Field(default_factory=PlayerAbilityScores, description="Ability scores.")
    saving_throws: PlayerSavingThrows = Field(default_factory=PlayerSavingThrows, description="Saving throws.")


class CharacterSkillsAndTricks(SchemaModel):
    skills: List[SkillEntry] = Field(default_factory=list, description="Skills and modifiers.")
    skill_tricks: List[str] = Field(default_factory=list, description="Skill tricks known.")


class CharacterFeats(SchemaModel):
    feats: List[str] = Field(default_factory=list, description="Feat IDs the character possesses.")
    bonus_feat_slots: int = Field(0, description="Number of unspent bonus feats.")


class CharacterClassDetails(SchemaModel):
    experience: int = Field(0, description="Current XP.")
    level: int = Field(0, description="Current character level.")
    effective_character_level: int = Field(0, description="Effective character level (includes LA).")
    level_adjustment: int = Field(0, description="Level adjustment.")
    challenge_rating: Optional[float] = Field(None, description="Challenge rating (for NPCs/monsters).")
    class_progression: List[ClassProgressionEntry] = Field(default_factory=list, description="Class levels.")
    special_abilities: List[ClassEffect] = Field(default_factory=list, description="Class features granted.")
    special_mechanics: List[SpecialMechanic] = Field(default_factory=list, description="Unique, stateful mechanics.")


class CharacterMagic(SchemaModel):
    spellcasting_by_class: List[PerClassCasting] = Field(default_factory=list, description="Per-class spellcasting.")
    maneuvers: Maneuvers = Field(default_factory=lambda: Maneuvers(), description="Martial maneuvers.")


# -----------------------------
# Content check aggregation
# -----------------------------

class CharacterContentCheckResult(SchemaModel):
    dependencies: Optional[List[ContentDependency]] = Field(None, description="Content dependencies for the character.")
