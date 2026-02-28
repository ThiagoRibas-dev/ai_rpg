from enum import StrEnum

# ---------------------------------------------------------------------------
# PREFAB IDENTIFIERS
# ---------------------------------------------------------------------------

class PrefabID(StrEnum):
    # Values
    VAL_INT = "VAL_INT"
    VAL_COMPOUND = "VAL_COMPOUND"
    VAL_STEP_DIE = "VAL_STEP_DIE"
    VAL_LADDER = "VAL_LADDER"
    VAL_BOOL = "VAL_BOOL"
    VAL_TEXT = "VAL_TEXT"
    
    # Resources
    RES_POOL = "RES_POOL"
    RES_COUNTER = "RES_COUNTER"
    RES_TRACK = "RES_TRACK"
    
    # Containers
    CONT_LIST = "CONT_LIST"
    CONT_TAGS = "CONT_TAGS"
    CONT_WEIGHTED = "CONT_WEIGHTED"


# ---------------------------------------------------------------------------
# CATEGORY NAMES
# ---------------------------------------------------------------------------

class CategoryName(StrEnum):
    IDENTITY = "identity"
    ATTRIBUTES = "attributes"
    RESOURCES = "resources"
    SKILLS = "skills"
    INVENTORY = "inventory"
    FEATURES = "features"
    PROGRESSION = "progression"
    COMBAT = "combat"
    STATUS = "status"
    META = "meta"
    NARRATIVE = "narrative"
    CONNECTIONS = "connections"


# ---------------------------------------------------------------------------
# INTERNAL FIELD KEYS (Prefab Shapes)
# ---------------------------------------------------------------------------

class FieldKey:
    # RES_POOL
    CURRENT = "current"
    MAX = "max"
    
    # VAL_COMPOUND
    SCORE = "score"
    MOD = "mod"
    
    # VAL_LADDER
    VALUE = "value"
    LABEL = "label"
    
    # CONT_LIST / CONT_WEIGHTED
    NAME = "name"
    QTY = "qty"
    WEIGHT = "weight"


# ---------------------------------------------------------------------------
# MANIFEST CONFIGURATION KEYS
# ---------------------------------------------------------------------------

class ConfigKey:
    DEFAULT = "default"
    DEFAULT_MAX = "default_max"
    ITEM_SHAPE = "item_shape"


# ---------------------------------------------------------------------------
# EXTRACTION SCHEMA KEYS (Mechanics & Procedures)
# ---------------------------------------------------------------------------

class ExtractionKey:
    # Mechanics
    DICE_NOTATION = "dice_notation"
    RESOLUTION_MECHANIC = "resolution_mechanic"
    SUCCESS_CONDITION = "success_condition"
    CRIT_RULES = "crit_rules"
    FUMBLE_RULES = "fumble_rules"
    ALIASES = "aliases"
    
    # Procedures
    COMBAT = "combat"
    EXPLORATION = "exploration"
    SOCIAL = "social"
    DOWNTIME = "downtime"
    CHARACTER_CREATION = "character_creation"
