"""
Prefab Registry
===============
Defines the Prefab dataclass and the global PREFABS dictionary.
Each prefab bundles: data shape, validator, UI widget hint, and AI description.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Literal

from app.prefabs.validators import (
    # Validators
    validate_int,
    validate_compound,
    validate_step_die,
    validate_ladder,
    validate_bool,
    validate_text,
    validate_pool,
    validate_counter,
    validate_track,
    validate_list,
    validate_tags,
    validate_weighted,
    # Default generators
    get_default_int,
    get_default_compound,
    get_default_step_die,
    get_default_ladder,
    get_default_bool,
    get_default_text,
    get_default_pool,
    get_default_counter,
    get_default_track,
    get_default_list,
    get_default_tags,
    get_default_weighted,
)


# =============================================================================
# PREFAB DATACLASS
# =============================================================================


@dataclass
class Prefab:
    """
    A prefab bundles vocabulary, validation, and rendering for a field type.
    
    Attributes:
        id: Unique identifier (e.g., "RES_POOL")
        family: Category for grouping ("VAL", "RES", "CONT")
        shape: Example data structure (for documentation)
        validate: Function (value, config) -> corrected_value
        get_default: Function (config) -> default_value
        widget: UI rendering hint
        ai_hint: One-line description for LLM context (<100 chars)
    """
    id: str
    family: Literal["VAL", "RES", "CONT"]
    shape: Any
    validate: Callable[[Any, Dict[str, Any]], Any]
    get_default: Callable[[Dict[str, Any]], Any]
    widget: str
    ai_hint: str


# =============================================================================
# PREFAB DEFINITIONS
# =============================================================================


PREFABS: Dict[str, Prefab] = {
    
    # -------------------------------------------------------------------------
    # VALUE FAMILY: Rarely-changing ratings
    # -------------------------------------------------------------------------
    
    "VAL_INT": Prefab(
        id="VAL_INT",
        family="VAL",
        shape="int",
        validate=validate_int,
        get_default=get_default_int,
        widget="number",
        ai_hint="Simple number. Use 'adjust' +/- or 'set' to change.",
    ),
    
    "VAL_COMPOUND": Prefab(
        id="VAL_COMPOUND",
        family="VAL",
        shape={"score": "int", "mod": "int"},
        validate=validate_compound,
        get_default=get_default_compound,
        widget="compound",
        ai_hint="Score with modifier (e.g., 18 -> +4). Set the score, mod auto-computes.",
    ),
    
    "VAL_STEP_DIE": Prefab(
        id="VAL_STEP_DIE",
        family="VAL",
        shape="str (d4/d6/d8/d10/d12)",
        validate=validate_step_die,
        get_default=get_default_step_die,
        widget="die_selector",
        ai_hint="Die type from chain. Use 'set' to change step (e.g., 'd6' to 'd8').",
    ),
    
    "VAL_LADDER": Prefab(
        id="VAL_LADDER",
        family="VAL",
        shape={"value": "int", "label": "str"},
        validate=validate_ladder,
        get_default=get_default_ladder,
        widget="ladder",
        ai_hint="Rated value with label (e.g., +2 = 'Fair'). Set the value, label auto-fills.",
    ),
    
    "VAL_BOOL": Prefab(
        id="VAL_BOOL",
        family="VAL",
        shape="bool",
        validate=validate_bool,
        get_default=get_default_bool,
        widget="toggle",
        ai_hint="True/false toggle. Use 'set' with true or false.",
    ),

    "VAL_TEXT": Prefab(
        id="VAL_TEXT",
        family="VAL",
        shape="str",
        validate=validate_text,
        get_default=get_default_text,
        widget="text_label",
        ai_hint="Simple text string (e.g. Deity, Class Path). Use 'set' to change."
    ),
    
    # -------------------------------------------------------------------------
    # RESOURCE FAMILY: Fluctuating values during play
    # -------------------------------------------------------------------------
    
    "RES_POOL": Prefab(
        id="RES_POOL",
        family="RES",
        shape={"current": "int", "max": "int"},
        validate=validate_pool,
        get_default=get_default_pool,
        widget="progress_bar",
        ai_hint="Current/max pool. Adjust 'path.current' for damage/healing. Auto-clamped to 0-max.",
    ),
    
    "RES_COUNTER": Prefab(
        id="RES_COUNTER",
        family="RES",
        shape="int",
        validate=validate_counter,
        get_default=get_default_counter,
        widget="counter",
        ai_hint="Simple counter (XP, gold). Use 'adjust' to add/subtract. Usually no max.",
    ),
    
    "RES_TRACK": Prefab(
        id="RES_TRACK",
        family="RES",
        shape=["bool", "bool", "..."],
        validate=validate_track,
        get_default=get_default_track,
        widget="checkbox_row",
        ai_hint="Sequential boxes. Use 'mark' to fill, negative to clear. Fills left-to-right.",
    ),
    
    # -------------------------------------------------------------------------
    # CONTAINER FAMILY: Lists and collections
    # -------------------------------------------------------------------------
    
    "CONT_LIST": Prefab(
        id="CONT_LIST",
        family="CONT",
        shape=[{"name": "str", "...": "any"}],
        validate=validate_list,
        get_default=get_default_list,
        widget="item_list",
        ai_hint="List of items. Use 'set' to replace entire list or modify path to specific item.",
    ),
    
    "CONT_TAGS": Prefab(
        id="CONT_TAGS",
        family="CONT",
        shape=["str", "str", "..."],
        validate=validate_tags,
        get_default=get_default_tags,
        widget="tag_list",
        ai_hint="Simple string list. Use 'set' to replace list.",
    ),
    
    "CONT_WEIGHTED": Prefab(
        id="CONT_WEIGHTED",
        family="CONT",
        shape=[{"name": "str", "weight": "float", "...": "any"}],
        validate=validate_weighted,
        get_default=get_default_weighted,
        widget="weighted_list",
        ai_hint="Items with weight for encumbrance. Each item has 'weight' field.",
    ),
}


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def get_prefab(prefab_id: str) -> Prefab:
    """
    Get a prefab by ID.
    
    Raises:
        KeyError: If prefab_id not found
    """
    if prefab_id not in PREFABS:
        raise KeyError(f"Unknown prefab ID: {prefab_id}")
    return PREFABS[prefab_id]


def list_prefabs(family: str = None) -> List[str]:
    """
    List all prefab IDs, optionally filtered by family.
    
    Args:
        family: "VAL", "RES", or "CONT" (or None for all)
    """
    if family is None:
        return list(PREFABS.keys())
    return [p.id for p in PREFABS.values() if p.family == family]


def validate_value(prefab_id: str, value: Any, config: Dict[str, Any] = None) -> Any:
    """
    Convenience function to validate a value using a prefab.
    
    Args:
        prefab_id: Prefab identifier
        value: Value to validate
        config: Prefab configuration
    
    Returns:
        Validated/corrected value
    """
    prefab = get_prefab(prefab_id)
    return prefab.validate(value, config or {})


def get_default_value(prefab_id: str, config: Dict[str, Any] = None) -> Any:
    """
    Get the default value for a prefab.
    
    Args:
        prefab_id: Prefab identifier
        config: Prefab configuration
    
    Returns:
        Default value
    """
    prefab = get_prefab(prefab_id)
    return prefab.get_default(config or {})


def get_ai_hints() -> str:
    """
    Generate AI context hints for all prefabs.
    Used in prompt building.
    """
    lines = ["## PREFAB TYPES\n"]
    
    for family, family_name in [("VAL", "Values"), ("RES", "Resources"), ("CONT", "Containers")]:
        lines.append(f"### {family_name}")
        for prefab in PREFABS.values():
            if prefab.family == family:
                lines.append(f"- **{prefab.id}**: {prefab.ai_hint}")
        lines.append("")
    
    return "\n".join(lines)
