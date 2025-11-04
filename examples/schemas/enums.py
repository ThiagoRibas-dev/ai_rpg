from enum import Enum

# Fallback for Python < 3.11 where enum.StrEnum is unavailable
try:
    from enum import StrEnum  # type: ignore
except Exception:
    class StrEnum(str, Enum):
        pass


class Skill(StrEnum):
    """An enumeration of all skills."""

    APPRAISE = "skill_appraise"
    BALANCE = "skill_balance"
    BLUFF = "skill_bluff"
    CLIMB = "skill_climb"
    CONCENTRATION = "skill_concentration"
    CRAFT = "skill_craft"
    DECIPHER_SCRIPT = "skill_decipher_script"
    DIPLOMACY = "skill_diplomacy"
    DISABLE_DEVICE = "skill_disable_device"
    DISGUISE = "skill_disguise"
    ESCAPE_ARTIST = "skill_escape_artist"
    FORGERY = "skill_forgery"
    GATHER_INFORMATION = "skill_gather_information"
    HANDLE_ANIMAL = "skill_handle_animal"
    HEAL = "skill_heal"
    HIDE = "skill_hide"
    INTIMIDATE = "skill_intimidate"
    JUMP = "skill_jump"
    KNOWLEDGE_ARCANA = "skill_knowledge_arcana"
    KNOWLEDGE_ARCHITECTURE = "skill_knowledge_architecture"
    KNOWLEDGE_DUNGEONEERING = "skill_knowledge_dungeoneering"
    KNOWLEDGE_GEOGRAPHY = "skill_knowledge_geography"
    KNOWLEDGE_HISTORY = "skill_knowledge_history"
    KNOWLEDGE_LOCAL = "skill_knowledge_local"
    KNOWLEDGE_NATURE = "skill_knowledge_nature"
    KNOWLEDGE_NOBILITY = "skill_knowledge_nobility"
    KNOWLEDGE_RELIGION = "skill_knowledge_religion"
    KNOWLEDGE_THE_PLANES = "skill_knowledge_the_planes"
    LISTEN = "skill_listen"
    MOVE_SILENTLY = "skill_move_silently"
    OPEN_LOCK = "skill_open_lock"
    PERFORM = "skill_perform"
    PROFESSION = "skill_profession"
    PSICRAFT = "skill_psicraft"
    RIDE = "skill_ride"
    SEARCH = "skill_search"
    SENSE_MOTIVE = "skill_sense_motive"
    SLEIGHT_OF_HAND = "skill_sleight_of_hand"
    SPEAK_LANGUAGE = "skill_speak_language"
    SPELLCRAFT = "skill_spellcraft"
    SPOT = "skill_spot"
    SURVIVAL = "skill_survival"
    SWIM = "skill_swim"
    TUMBLE = "skill_tumble"
    TRUENAMING = "skill_truenaming"
    USE_MAGIC_DEVICE = "skill_use_magic_device"
    USE_PSIONIC_DEVICE = "skill_use_psionic_device"
    USE_ROPE = "skill_use_rope"


class Stat(StrEnum):
    """All modifiable stats addressable by ModifierEffect."""

    # Core Abilities
    STRENGTH = "strength"
    DEXTERITY = "dexterity"
    CONSTITUTION = "constitution"
    INTELLIGENCE = "intelligence"
    WISDOM = "wisdom"
    CHARISMA = "charisma"

    # Combat Stats
    HIT_POINTS = "hit_points"
    ACTION_POINTS = "action_points"
    ARMOR_CLASS = "armor_class"
    ARMOR_CLASS_TOUCH = "armor_class_touch"
    ARMOR_CLASS_FLAT_FOOTED = "armor_class_flat_footed"

    INITIATIVE = "initiative"
    BASE_ATTACK_BONUS = "base_attack_bonus"
    GRAPPLE = "grapple"
    SPELL_RESISTANCE = "spell_resistance"
    DAMAGE_REDUCTION = "damage_reduction"
    ARMOR_CHECK_PENALTY = "armor_check_penalty"

    # Saving Throws
    FORTITUDE_SAVE = "fortitude_save"
    REFLEX_SAVE = "reflex_save"
    WILL_SAVE = "will_save"

    # Movement (base + flags)
    MOVEMENT_SPEED_BASE = "movement_speed_base"
    MOVEMENT_IGNORE_ARMOR_PENALTY = "movement_ignore_armor_penalty"
    MOVEMENT_IGNORE_LOAD_PENALTY = "movement_ignore_load_penalty"

    # Vision (kept for compatibility with effect targets; prefer SenseType for new content)
    VISION_DARKVISION_RANGE = "vision_darkvision_range"
    VISION_LOWLIGHT_RANGE = "vision_lowlight_range"

    # Magic
    CASTER_LEVEL = "caster_level"
    CONCENTRATION_CHECK = "concentration_check"
    SPELL_SAVE_DC = "spell_save_dc"

    # Spellcasting Progression
    DIVINE_SPELLCASTING_PROGRESSION = "divine_spellcasting_progression"
    ARCANE_SPELLCASTING_PROGRESSION = "arcane_spellcasting_progression"
    PSIONIC_SPELLCASTING_PROGRESSION = "psionic_spellcasting_progression"

    # Martial Maneuvers
    INITIATOR_LEVEL = "initiator_level"

    # Bonus Skill Points
    SKILL_POINTS = "skill_points"
    SKILL_POINT_GAIN = "skill_point_gain"

    # Skills
    APPRAISE = Skill.APPRAISE.value
    BALANCE = Skill.BALANCE.value
    BLUFF = Skill.BLUFF.value
    CLIMB = Skill.CLIMB.value
    CONCENTRATION = Skill.CONCENTRATION.value
    CRAFT = Skill.CRAFT.value
    DECIPHER_SCRIPT = Skill.DECIPHER_SCRIPT.value
    DIPLOMACY = Skill.DIPLOMACY.value
    DISABLE_DEVICE = Skill.DISABLE_DEVICE.value
    DISGUISE = Skill.DISGUISE.value
    ESCAPE_ARTIST = Skill.ESCAPE_ARTIST.value
    FORGERY = Skill.FORGERY.value
    GATHER_INFORMATION = Skill.GATHER_INFORMATION.value
    HANDLE_ANIMAL = Skill.HANDLE_ANIMAL.value
    HEAL = Skill.HEAL.value
    HIDE = Skill.HIDE.value
    INTIMIDATE = Skill.INTIMIDATE.value
    JUMP = Skill.JUMP.value
    KNOWLEDGE_ARCANA = Skill.KNOWLEDGE_ARCANA.value
    KNOWLEDGE_ARCHITECTURE = Skill.KNOWLEDGE_ARCHITECTURE.value
    KNOWLEDGE_DUNGEONEERING = Skill.KNOWLEDGE_DUNGEONEERING.value
    KNOWLEDGE_GEOGRAPHY = Skill.KNOWLEDGE_GEOGRAPHY.value
    KNOWLEDGE_HISTORY = Skill.KNOWLEDGE_HISTORY.value
    KNOWLEDGE_LOCAL = Skill.KNOWLEDGE_LOCAL.value
    KNOWLEDGE_NATURE = Skill.KNOWLEDGE_NATURE.value
    KNOWLEDGE_NOBILITY = Skill.KNOWLEDGE_NOBILITY.value
    KNOWLEDGE_RELIGION = Skill.KNOWLEDGE_RELIGION.value
    KNOWLEDGE_THE_PLANES = Skill.KNOWLEDGE_THE_PLANES.value
    LISTEN = Skill.LISTEN.value
    MOVE_SILENTLY = Skill.MOVE_SILENTLY.value
    OPEN_LOCK = Skill.OPEN_LOCK.value
    PERFORM = Skill.PERFORM.value
    PROFESSION = Skill.PROFESSION.value
    PSICRAFT = Skill.PSICRAFT.value
    RIDE = Skill.RIDE.value
    SEARCH = Skill.SEARCH.value
    SENSE_MOTIVE = Skill.SENSE_MOTIVE.value
    SLEIGHT_OF_HAND = Skill.SLEIGHT_OF_HAND.value
    SPEAK_LANGUAGE = Skill.SPEAK_LANGUAGE.value
    SPELLCRAFT = Skill.SPELLCRAFT.value
    SPOT = Skill.SPOT.value
    SURVIVAL = Skill.SURVIVAL.value
    SWIM = Skill.SWIM.value
    TUMBLE = Skill.TUMBLE.value
    TRUENAMING = Skill.TRUENAMING.value
    USE_MAGIC_DEVICE = Skill.USE_MAGIC_DEVICE.value
    USE_PSIONIC_DEVICE = Skill.USE_PSIONIC_DEVICE.value
    USE_ROPE = Skill.USE_ROPE.value

    # Additional movement modes, size, and temp HP
    FLY_SPEED = "fly_speed"
    CLIMB_SPEED = "climb_speed"
    SWIM_SPEED = "swim_speed"
    BURROW_SPEED = "burrow_speed"

    SIZE_CATEGORY = "size_category"
    TEMPORARY_HIT_POINTS = "temporary_hit_points"


class BonusType(StrEnum):
    """3.5e bonus types for stacking rules."""
    ENHANCEMENT = "enhancement"
    SACRED = "sacred"
    PROFANE = "profane"
    ARMOR = "armor"
    SHIELD = "shield"
    NATURAL_ARMOR = "natural_armor"
    DEFLECTION = "deflection"
    DODGE = "dodge"
    CIRCUMSTANCE = "circumstance"
    COMPETENCE = "competence"
    INSIGHT = "insight"
    LUCK = "luck"
    MORALE = "morale"
    RACIAL = "racial"
    SIZE = "size"
    INHERENT = "inherent"
    UNTYPED = "untyped"


class DurationType(StrEnum):
    """Effect duration units."""
    INSTANTANEOUS = "instantaneous"
    PERMANENT = "permanent"
    ROUNDS = "rounds"
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"
    ENCOUNTER = "encounter"
    SPECIAL = "special"


class EffectType(StrEnum):
    """All possible effect types."""
    ACTION_OPTION = "action_option"
    BONUS_FEAT = "bonus_feat"
    GRANT_ABILITY = "grant_ability"
    GRANT_BONUS_FEAT_CHOICE = "grant_bonus_feat_choice"
    GRANT_CHOICE = "grant_choice"
    GRANT_COHORT = "grant_cohort"
    GRANT_FEAT = "grant_feat"
    GRANT_MANEUVER_CHOICE = "grant_maneuver_choice"
    GRANT_PROFICIENCY = "grant_proficiency"
    GRANT_STANCE_CHOICE = "grant_stance_choice"
    MANEUVER_PROGRESSION = "maneuver_progression"
    METAMAGIC = "metamagic"
    MODIFIER = "modifier"
    TEMPORARY_IMMUNITY = "temporary_immunity"

    HP_CHANGE = "hp_change"

    CONDITION = "condition"
    DAMAGE_REDUCTION = "damage_reduction"
    RESISTANCE = "resistance"
    HEALING_OVER_TIME = "healing_over_time"
    SENSE = "sense"
    ROLL_MODIFIER = "roll_modifier"
    NEGATIVE_LEVEL = "negative_level"
    ABILITY_DAMAGE = "ability_damage"
    AFFLICTION = "affliction"
    SPELL_LIKE_ABILITY = "spell_like_ability"
    RESOURCE_POOL = "resource_pool"
    WEAPON_PROPERTY = "weapon_property"
    MOVEMENT_MODE = "movement_mode"
    TEMPORARY_HP = "temporary_hp"
    SUMMONING_AUGMENT = "summoning_augment"


class SizeCategory(StrEnum):
    FINE = "fine"
    DIMINUTIVE = "diminutive"
    TINY = "tiny"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    HUGE = "huge"
    GARGANTUAN = "gargantuan"
    COLOSSAL = "colossal"


class ConditionalType(StrEnum):
    """Context/gating predicates (timing uses TriggerEvent, numeric uses ComparisonKey/Op)."""
    ACTION_TYPE = "action_type"
    CASTER_RACE = "caster_race"
    CASTING_SPELL_TYPE = "casting_spell_type"
    CHARACTER_LEVEL = "character_level"
    CUSTOM_CONDITION = "custom_condition"
    HAS_SPELL_AVAILABLE = "has_spell_available"
    IN_SUNLIGHT = "in_sunlight"
    IS_ACTIVE = "is_active"
    IS_ALLY = "is_ally"
    IS_CASTER = "is_caster"
    TARGET_ALIGNMENT = "target_alignment"
    TARGET_HAS_TYPE = "target_has_type"
    TARGET_RACE = "target_race"
    UNARMORED = "unarmored"
    CARRYING_MEDIUM_OR_HEAVY_LOAD = "carrying_medium_or_heavy_load"
    WITH_WEAPON_GROUP = "with_weapon_group"
    WITH_WEAPON_ID = "with_weapon_id"
    WITHIN_AREA = "within_area"


class ProficiencyCategory(StrEnum):
    WEAPON = "weapon"
    ARMOR = "armor"
    SKILL = "skill"


class Condition(StrEnum):
    BLINDED = "blinded"
    BLOWN_AWAY = "blown_away"
    CHECKED = "checked"
    DAZED = "dazed"
    DAZZLED = "dazzled"
    DEAD = "dead"
    DEAFENED = "deafened"
    DISABLED = "disabled"
    DYING = "dying"
    CONFUSED = "confused"
    COWERING = "cowering"
    ENERGY_DRAINED = "energy_drained"
    ENTANGLED = "entangled"
    EXHAUSTED = "exhausted"
    FASCINATED = "fascinated"
    FATIGUED = "fatigued"
    FLAT_FOOTED = "flat_footed"
    FRIGHTENED = "frightened"
    GRAPPLING = "grappling"
    HELPLESS = "helpless"
    INCORPOREAL = "incorporeal"
    INVISIBLE = "invisible"
    NAUSEATED = "nauseated"
    PANICKED = "panicked"
    PARALYZED = "paralyzed"
    PETRIFIED = "petrified"
    PINNED = "pinned"
    PRONE = "prone"
    SHAKEN = "shaken"
    SICKENED = "sickened"
    STABLE = "stable"
    STAGGERED = "staggered"
    STUNNED = "stunned"
    TURNED = "turned"
    UNCONSCIOUS = "unconscious"


class EnergyType(StrEnum):
    ACID = "acid"
    COLD = "cold"
    ELECTRICITY = "electricity"
    FIRE = "fire"
    SONIC = "sonic"
    NEGATIVE = "negative"
    POSITIVE = "positive"
    DISSICATION = "dissication"
    FORSTBURN = "frostburn"


class HPChangeType(StrEnum):
    ACID = "acid"
    COLD = "cold"
    ELECTRICITY = "electricity"
    FIRE = "fire"
    SONIC = "sonic"
    FORCE = "force"
    NEGATIVE = "negative"
    POSITIVE = "positive"
    BLUDGEONING = "bludgeoning"
    PIERCING = "piercing"
    SLASHING = "slashing"
    HEALING = "healing"
    UNTYPED = "untyped"


class DRBypass(StrEnum):
    MAGIC = "magic"
    EPIC = "epic"
    ADAMANTINE = "adamantine"
    SILVER = "silver"
    COLD_IRON = "cold_iron"
    GOOD = "good"
    EVIL = "evil"
    LAWFUL = "lawful"
    CHAOTIC = "chaotic"
    BLUDGEONING = "bludgeoning"
    PIERCING = "piercing"
    SLASHING = "slashing"


class SenseType(StrEnum):
    DARKVISION = "darkvision"
    LOW_LIGHT = "low_light"
    BLINDSIGHT = "blindsight"
    BLINDSENSE = "blindsense"
    SCENT = "scent"
    TREMORSENSE = "tremorsense"
    MINDSIGHT = "mindsight"


class MovementMode(StrEnum):
    LAND = "land"
    FLY = "fly"
    CLIMB = "climb"
    SWIM = "swim"
    BURROW = "burrow"


class TriggerEvent(StrEnum):
    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"
    ON_HIT = "on_hit"
    ON_CRITICAL_HIT = "on_critical_hit"
    ON_DAMAGE_DEALT = "on_damage_dealt"
    ON_SAVE_FAILED = "on_save_failed"
    ON_CAST_SPELL = "on_cast_spell"
    ON_SPELL_RESOLVED = "on_spell_resolved"
    START_OF_TURN = "start_of_turn"
    END_OF_TURN = "end_of_turn"
    ENTERS_SUNLIGHT = "enters_sunlight"
    LEAVES_AREA = "leaves_area"


class RefreshCycle(StrEnum):
    PER_DAY = "per_day"
    PER_ENCOUNTER = "per_encounter"
    PER_WEEK = "per_week"
    SPECIAL = "special"


class AttackType(StrEnum):
    MELEE = "melee"
    RANGED = "ranged"
    NATURAL = "natural"
    UNARMED = "unarmed"


class RollType(StrEnum):
    ATTACK = "attack"
    DAMAGE = "damage"


class DRLogic(StrEnum):
    ANY = "any"
    ALL = "all"


class HealOverTimeMode(StrEnum):
    FAST_HEALING = "fast_healing"
    REGENERATION = "regeneration"


class Maneuverability(StrEnum):
    CLUMSY = "clumsy"
    POOR = "poor"
    AVERAGE = "average"
    GOOD = "good"
    PERFECT = "perfect"


class CombatManeuver(StrEnum):
    TRIP = "trip"
    DISARM = "disarm"
    BULL_RUSH = "bull_rush"
    GRAPPLE = "grapple"
    OVERRUN = "overrun"
    SUNDER = "sunder"
    FEINT = "feint"
    AID_ANOTHER = "aid_another"


class AlignmentTag(StrEnum):
    GOOD = "good"
    EVIL = "evil"
    LAWFUL = "lawful"
    CHAOTIC = "chaotic"
    NEUTRAL = "neutral"


class AbilityShort(StrEnum):
    STR = "str"
    DEX = "dex"
    CON = "con"
    INT = "int"
    WIS = "wis"
    CHA = "cha"


class SpellSchool(StrEnum):
    ABJURATION = "Abjuration"
    CONJURATION = "Conjuration"
    DIVINATION = "Divination"
    ENCHANTMENT = "Enchantment"
    EVOCATION = "Evocation"
    ILLUSION = "Illusion"
    NECROMANCY = "Necromancy"
    TRANSMUTATION = "Transmutation"
    UNIVERSAL = "Universal"


class SpellSubschool(StrEnum):
    BOOST = "Boost"
    CALLING = "Calling"
    CHARM = "Charm"
    COMPULSION = "Compulsion"
    COUNTER = "Counter"
    CREATION = "Creation"
    CREATION_OR_CALLING = "Creation or Calling"
    FIGMENT = "Figment"
    FIGMENT_AND_GLAMER = "Figment and Glamer"
    GLAMER = "Glamer"
    HEALING = "Healing"
    PATTERN = "Pattern"
    PHANTASM = "Phantasm"
    POLYMORPH = "Polymorph"
    SCRYING = "Scrying"
    SHADOW = "Shadow"
    STANCE = "Stance"
    STRIKE = "Strike"
    SUMMONING = "Summoning"
    TELEPORTATION = "Teleportation"
    NONE = "None"


class CastingTimeUnit(StrEnum):
    STANDARD_ACTION = "standard_action"
    FULL_ROUND = "full_round"
    ROUND = "round"
    MINUTE = "minute"
    HOUR = "hour"
    SWIFT = "swift"
    IMMEDIATE = "immediate"


class SaveType(StrEnum):
    FORTITUDE = "fortitude"
    REFLEX = "reflex"
    WILL = "will"


class SaveEffect(StrEnum):
    NEGATES = "negates"
    HALF = "half"
    PARTIAL = "partial"
    HARMS = "harms"
    HARMLESS = "harmless"
    OBJECT = "object"
    SEE_TEXT = "see_text"


class AfflictionType(StrEnum):
    POISON = "poison"
    DISEASE = "disease"


class ComparisonKey(StrEnum):
    """Left/right-hand keys for numeric comparisons in conditionals."""
    CASTER_LEVEL = "caster_level"
    TARGET_HD = "target_hd"
    TARGET_HP = "target_hp"
    TARGET_HP_PERCENT = "target_hp_percent"
    CHARACTER_LEVEL = "character_level"
    DISTANCE = "distance"
    SLOT_LEVEL = "slot_level"
    ARMOR_WORN = "armor_worn"
    LOAD_CATEGORY = "load_category"
    DEITY = "deity"


class ComparisonOp(StrEnum):
    EQ = "eq"
    NE = "ne"
    LT = "lt"
    LTE = "lte"
    GT = "gt"
    GTE = "gte"