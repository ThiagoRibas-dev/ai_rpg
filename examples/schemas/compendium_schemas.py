from pydantic import Field
from typing import List, Optional
from enum import Enum


# Fallback for Python < 3.11 where enum.StrEnum is unavailable
try:
    from enum import StrEnum  # type: ignore
except Exception:
    class StrEnum(str, Enum):
        pass


from app.schemas.effects_modular import Dice
from app.schemas.prerequisites import PrerequisiteType
from app.schemas.effects import (
    RaceEffect,
    ClassEffect,
    FeatEffect,
    ItemEffect,
    SpellEffect,
    PowerEffect,
)
from .base import SchemaModel
from .enums import (
    Skill,
    SpellSchool,
    SpellSubschool,
    CastingTimeUnit,
    SaveType,
    SaveEffect,
)


class CompendiumCategory(StrEnum):
    """Defines the standard category names for the compendium."""
    CLASSES = "Classes"
    RACES = "Races"
    FEATS = "Feats"
    ITEMS = "Items"
    SPELLS = "Spells"
    PSIONICS = "Psionics"
    MONSTERS = "Monsters"
    RULES = "Rules"


class PsionicDiscipline(StrEnum):
    """Enum for psionic disciplines."""
    CLAIRSENTIENCE = "Clairsentience"
    METACREATIVITY = "Metacreativity"
    PSYCHOKINESIS = "Psychokinesis"
    PSYCHOMETABOLISM = "Psychometabolism"
    PSYCHOPORTATION = "Psychoportation"
    TELEPATHY = "Telepathy"
    GENERAL = "General"


class PsionicSubDiscipline(StrEnum):
    """Enum for psionic subdisciplines."""
    NONE = "None"


class SpellComponent(StrEnum):
    """Enum for spell components."""
    VERBAL = "V"
    SOMATIC = "S"
    MATERIAL = "M"
    FOCUS = "F"
    DIVINE_FOCUS = "DF"
    XP_COST = "XP"
    ARCANE_FOCUS = "AF"
    SPECIFIC_MATERIAL = "Specific Material"
    SACRIFICE = "Sacrifice"


class FeatType(StrEnum):
    """Enum for feat types (broad, extensible set)."""
    GENERAL = "General"
    ABERRANT = "Aberrant"
    ABYSSAL_HERITOR = "Abyssal Heritor"
    AMBUSH = "Ambush"
    BARDIC_MUSIC = "Bardic Music"
    BREATH = "Breath"
    CEREMONY = "Ceremony"
    COMBAT_FORM = "Combat Form"
    DEVIL_TOUCHED = "Devil-Touched"
    DIVINE = "Divine"
    DOMAIN = "Domain"
    DRACONIC = "Draconic"
    FIGHTER = "Fighter"
    EPIC = "Epic"
    EXALTED = "Exalted"
    HERITAGE = "Heritage"
    HOST = "Host"
    INCARNUM = "Incarnum"
    INITIATE = "Initiate"
    ITEM_CREATION = "Item Creation"
    LEGACY = "Legacy"
    LUCK = "Luck"
    METABREATH = "Metabreath"
    METAMAGIC = "Metamagic"
    METAPSIONIC = "Metapsionic"
    MONSTROUS = "Monstrous"
    PSIONIC = "Psionic"
    PSIONIC_ITEM_CREATION = "Psionic Item Creation"
    RACIAL = "Racial"
    RECITATION = "Recitation"
    RESERVE = "Reserve"
    SHIFTER = "Shifter"
    TACTICAL = "Tactical"
    VILE = "Vile"
    WEAPON_STYLE = "Weapon Style"
    WILD = "Wild"


class ClassType(StrEnum):
    """Enum for class types."""
    CHARACTER_CLASS = "Character Class"
    RACIAL_HIT_DICE = "Racial Hit Dice"
    PRESTIGE_CLASS = "Prestige Class"
    NPC_CLASS = "NPC Class"


class AbilityAdjustments(SchemaModel):
    """Represents adjustments to a creature's ability scores."""
    strength: int = Field(0, description="Adjustment to Strength score.")
    dexterity: int = Field(0, description="Adjustment to Dexterity score.")
    constitution: int = Field(0, description="Adjustment to Constitution score.")
    intelligence: int = Field(0, description="Adjustment to Intelligence score.")
    wisdom: int = Field(0, description="Adjustment to Wisdom score.")
    charisma: int = Field(0, description="Adjustment to Charisma score.")


class LanguageInfo(SchemaModel):
    """Represents the languages a race knows."""
    automatic: List[str] = Field(default_factory=list, description="Languages the race knows automatically.")
    bonus: List[str] = Field(default_factory=list, description="Bonus languages the race can choose from.")


class CompendiumRace(SchemaModel):
    """Represents a race entry in the compendium."""
    race_id: str = Field(..., description="A unique identifier for this race.")
    name: str = Field(..., description="The name of the race.")
    description: str = Field(..., description="A description of the race.")
    subrace_of: Optional[str] = Field(None, description="The race_id of the parent race, if this is a subrace.")
    size: str = Field(..., description="Creature's size (e.g., 'Medium', 'Small').")
    type: str = Field(..., description="Creature's type (e.g., 'Humanoid').")
    subtypes: List[str] = Field(default_factory=list, description="List of subtypes (e.g., 'Dwarf', 'Elf').")
    base_speed_ft: int = Field(..., description="Base movement speed in feet.")
    ability_adjustments: AbilityAdjustments = Field(default_factory=AbilityAdjustments, description="Adjustments to ability scores.")
    racial_traits: List[RaceEffect] = Field(default_factory=list, description="List of special qualities or racial traits.")
    languages: LanguageInfo = Field(default_factory=LanguageInfo, description="Languages the race knows.")
    favored_class: str = Field(..., description="The favored class for this race, or 'any'.")
    level_adjustment: int = Field(0, description="Level adjustment for calculating ECL.")
    racial_class_id: Optional[str] = Field(None, description="The class_id for the race's hit dice progression, if any.")


class SpellsPerDay(SchemaModel):
    """Represents spells per day for each spell level (0-9)."""
    level_0: int = Field(0, alias="0", description="Number of 0-level (cantrip/orisons) spells per day.")
    level_1: int = Field(0, alias="1", description="Number of 1st-level spells per day.")
    level_2: int = Field(0, alias="2", description="Number of 2nd-level spells per day.")
    level_3: int = Field(0, alias="3", description="Number of 3rd-level spells per day.")
    level_4: int = Field(0, alias="4", description="Number of 4th-level spells per day.")
    level_5: int = Field(0, alias="5", description="Number of 5th-level spells per day.")
    level_6: int = Field(0, alias="6", description="Number of 6th-level spells per day.")
    level_7: int = Field(0, alias="7", description="Number of 7th-level spells per day.")
    level_8: int = Field(0, alias="8", description="Number of 8th-level spells per day.")
    level_9: int = Field(0, alias="9", description="Number of 9th-level spells per day.")


class ClassLevel(SchemaModel):
    """Represents the progression data for a single level of a class."""
    level: int = Field(..., description="The specific level this class entry describes.")
    base_attack_bonus_gain: int = Field(0, description="The incremental Base Attack Bonus gained at this level.")
    fortitude_save_gain: int = Field(0, description="The incremental Fortitude save bonus gained at this level.")
    reflex_save_gain: int = Field(0, description="The incremental Reflex save bonus gained at this level.")
    will_save_gain: int = Field(0, description="The incremental Will save bonus gained at this level.")
    skill_points_gain: int = Field(0, description="The base number of skill points gained at this level.")
    features_gained: List[ClassEffect] = Field(default_factory=list, description="List of class features gained at this specific level.")


class SpellcastingInfo(SchemaModel):
    """Defines the core spellcasting attributes of a class."""
    spellcasting_type: str = Field(..., description="The type of spellcasting (e.g., 'arcane', 'divine').")
    ability_score: str = Field(..., description="The ability score used for spellcasting (e.g., 'intelligence', 'charisma').")
    spell_list_id: str = Field(..., description="The ID of the spell list used by this class.")


class CompendiumClass(SchemaModel):
    """Represents the full progression of a D&D class across all levels."""
    class_id: str = Field(..., description="A unique identifier for the class (e.g., 'fighter', 'cleric').")
    name: str = Field(..., description="The full name of the class (e.g., 'Fighter', 'Cleric').")
    class_type: ClassType = Field(..., description="The type of class.")
    description: str = Field(..., description="A description of the class.")
    prerequisites: List[PrerequisiteType] = Field(default_factory=list, description="A list of prerequisites to take this class.")
    hit_die: int = Field(..., description="The hit die for this class (e.g., 8 for 1d8, 10 for 1d10).")
    class_skills: List[Skill] = Field(..., description="List of class skills.")
    quadruple_skill_points_at_first_level: bool = Field(True, description="Whether skill points are quadrupled at 1st level.")
    spellcasting_info: Optional[SpellcastingInfo] = Field(None, description="Information about the class's spellcasting abilities.")
    is_martial_adept: bool = Field(False, description="True if this is a martial adept class (e.g., Crusader, Swordsage, Warblade).")
    level_progression: List[ClassLevel] = Field(default_factory=list, description="A list of ClassLevel objects detailing progression for each level.")


class CompendiumFeat(SchemaModel):
    """Represents a single feat."""
    feat_id: str = Field(..., description="A unique identifier for this feat.")
    name: str = Field(..., description="The name of the feat.")
    types: List[FeatType] = Field(default_factory=list, description="The types of the feat.")
    description: str = Field(..., description="A description of what this feat does.")
    prerequisites: List[PrerequisiteType] = Field(default_factory=list, description="A list of prerequisites to take this feat.")
    effects: List[FeatEffect] = Field(default_factory=list, description="A list of effects this feat provides.")
    special: Optional[str] = Field(None, description="Any special notes about the feat.")


class SpellLevel(SchemaModel):
    """Represents a combination of level and class for a spell."""
    level: int = Field(..., description="The spell's level.")
    class_id: str = Field(..., description="A unique identifier for the class (e.g., 'cleric', 'wizard').")


class MaterialComponent(SchemaModel):
    """Represents a material component or focus for a spell."""
    name: str = Field(..., description="The name of the component.")
    cost_gp: int = Field(0, description="The cost of the component in gold pieces.")
    is_focus: bool = Field(False, description="Whether the component is a focus (not consumed).")


class CastingTime(SchemaModel):
    """Represents the casting time of a spell."""
    value: float = Field(..., description="The numerical value of the casting time.")
    unit: CastingTimeUnit = Field(..., description="The unit of time (e.g., 'standard_action', 'swift', 'immediate', 'round', 'minute', 'hour', 'full_round').")


class Range(SchemaModel):
    """Represents the range of a spell."""
    type: str = Field(..., description="The type of range (e.g., 'personal', 'touch', 'close', 'medium', 'long', 'fixed').")
    base_value_ft: Optional[int] = Field(None, description="The base range in feet, if applicable.")
    per_level_ft: Optional[int] = Field(None, description="The additional range per caster level, if applicable.")


class Target(SchemaModel):
    """Represents the target of a spell."""
    type: str = Field(..., description="The type of target (e.g., 'creature', 'object', 'you').")
    number_of_targets: Optional[int] = Field(None, description="The number of targets the spell can affect.")
    restrictions: Optional[str] = Field(None, description="Any restrictions on the target (e.g., 'humanoid', 'living').")


class Area(SchemaModel):
    """Represents the area of effect of a spell."""
    shape: str = Field(..., description="The shape of the area (e.g., 'sphere', 'cone', 'line').")
    value_ft: int = Field(..., description="The size of the area in feet.")


class Duration(SchemaModel):
    """Represents the duration of a spell."""
    type: str = Field(..., description="The type of duration (e.g., 'instantaneous', 'concentration', 'timed').")
    value: Optional[int] = Field(None, description="The numerical value of the duration, if applicable.")
    unit: Optional[str] = Field(None, description="The unit of time for the duration, if applicable.")
    dismissible: bool = Field(False, description="Whether the spell can be dismissed.")


class SavingThrow(SchemaModel):
    """Represents the saving throw for a spell."""
    save_type: SaveType = Field(..., description="The type of save (fortitude, reflex, will).")
    effect: SaveEffect = Field(..., description="The effect of a successful save (negates, half, partial, harmless, object, see_text).")
    harmless: bool = Field(False, description="Whether the spell is harmless.")


class SpellResistanceInfo(SchemaModel):
    """Represents how spell resistance applies to a spell."""
    applicable: bool = Field(..., description="Whether spell resistance applies.")
    harmless: bool = Field(False, description="Whether the spell is harmless.")


class Spell(SchemaModel):
    """Represents a single spell."""
    spell_id: str = Field(..., description="A unique identifier for this spell.")
    name: str = Field(..., description="The name of the spell.")
    level: List[SpellLevel] = Field(default_factory=list, description="The list of levels for different classes.")
    components: List[SpellComponent] = Field(default_factory=list, description="List of the spell's components.")
    material_components: List[MaterialComponent] = Field(default_factory=list, description="List of material components and foci.")
    school: SpellSchool = Field(..., description="The school of magic.")
    subschool: Optional[SpellSubschool] = Field(None, description="The subschool, if any.")
    descriptors: List[str] = Field(default_factory=list, description="List of descriptors (e.g., 'Fire', 'Mind-Affecting').")
    casting_time: CastingTime = Field(..., description="The time required to cast the spell.")
    range: Range = Field(..., description="The range of the spell.")
    target: Optional[Target] = Field(None, description="The target of the spell.")
    area: Optional[Area] = Field(None, description="The area of effect of the spell.")
    duration: Duration = Field(..., description="The duration of the spell.")
    saving_throw: Optional[SavingThrow] = Field(None, description="The saving throw for the spell.")
    spell_resistance: SpellResistanceInfo = Field(..., description="How spell resistance applies to the spell.")
    effects: List[SpellEffect] = Field(default_factory=list, description="A list of the spell's effects.")
    description: str = Field(..., description="A detailed description of the spell's effect.")


class PowerLevel(SchemaModel):
    """Represents a combination of level and class for a psionic power."""
    level: int = Field(..., description="The power's level.")
    class_id: str = Field(..., description="A unique identifier for the class (e.g., 'psion', 'psychic_warrior').")


class PsionicPower(SchemaModel):
    """Represents a single psionic power."""
    power_id: str = Field(..., description="A unique identifier for this power.")
    name: str = Field(..., description="The name of the power.")
    level: List[PowerLevel] = Field(default_factory=list, description="The list of levels for different classes.")
    discipline: PsionicDiscipline = Field(..., description="The psionic discipline.")
    subdiscipline: Optional[PsionicSubDiscipline] = Field(None, description="The subdiscipline, if any.")
    descriptors: List[str] = Field(default_factory=list, description="List of descriptors (e.g., 'Mind-Affecting').")
    display: str = Field(..., description="Visual or sensory effect of manifesting the power.")
    manifesting_time: str = Field(..., description="The time required to manifest the power.")
    power_points: int = Field(..., description="The cost in power points to manifest the power.")
    effects: List[PowerEffect] = Field(default_factory=list, description="A list of the power's effects.")
    description: str = Field(..., description="A detailed description of the power's effect.")


class WeaponDetails(SchemaModel):
    """Details specific to a weapon item."""
    damage_dice: Dice = Field(..., description="The dice for the weapon's damage.")
    critical_range: str = Field(..., description="The critical threat range (e.g., '19-20', '20').")
    critical_mult: int = Field(..., description="The critical multiplier (e.g., 2 for x2, 3 for x3).")
    damage_types: List[str] = Field(..., description="A list of damage types (e.g., 'Slashing', 'Piercing', 'Bludgeoning').")
    range_increment_ft: int = Field(..., description="The range increment in feet for ranged weapons.")
    damage_mod: str = Field(..., description="The ability modifier applied to damage (e.g., 'Str', 'Dex').")


class ArmorDetails(SchemaModel):
    """Details specific to an armor item."""
    armor_bonus: int = Field(..., description="The armor bonus provided by the armor.")
    max_dex_bonus: Optional[int] = Field(None, description="The maximum Dexterity bonus allowed by the armor.")
    armor_check_penalty: int = Field(..., description="The armor check penalty applied to certain skill checks.")
    spell_failure_chance: float = Field(..., description="The arcane spell failure chance as a percentage (e.g., 0.2 for 20%).")


class ConsumableDetails(SchemaModel):
    """Details specific to a consumable item."""
    effects: List[ItemEffect] = Field(default_factory=list, description="A list of the consumable's effects when used.")
    charges: int = Field(..., description="The number of charges or uses the consumable has.")


class ItemUses(SchemaModel):
    """Tracks the total and current uses of an item with limited charges."""
    total: Optional[int] = Field(None, description="The total number of uses the item originally had.")
    current: Optional[int] = Field(None, description="The current number of remaining uses for the item.")


class Item(SchemaModel):
    """Represents a single item."""
    item_id: str = Field(..., description="A unique identifier for this item.")
    name: str = Field(..., description="The name of the item.")
    type: str = Field(..., description="The type of item (e.g., 'weapon', 'armor', 'potion').")
    slot: Optional[str] = Field(None, description="The equipment slot the item uses (e.g., 'hand1', 'head', 'ring').")
    properties: List[ItemEffect] = Field(default_factory=list, description="List of special properties or magical effects.")
    enhancement_bonus: int = Field(0, description="The item's enhancement bonus (e.g., +1, +2).")
    weight_lbs: float = Field(..., description="The item's weight in pounds.")
    cost_gp: int = Field(..., description="The item's cost in gold pieces.")
    description: str = Field(..., description="A description of the item.")
    weapon_details: Optional[WeaponDetails] = Field(None, description="Specific details if the item is a weapon.")
    armor_details: Optional[ArmorDetails] = Field(None, description="Specific details if the item is armor.")
    consumable_details: Optional[ConsumableDetails] = Field(None, description="Specific details if the item is a consumable.")
    uses: Optional[ItemUses] = Field(None, description="Information about the item's limited uses or charges.")