"""
Prefab Validators
=================
Pure functions that validate and correct values based on prefab type.
Each validator takes (value, config) and returns the corrected value.
No exceptions raised - always return a sensible default on bad input.
"""

from typing import Any, Dict, List


# =============================================================================
# VALUE VALIDATORS
# =============================================================================


def validate_int(value: Any, config: Dict[str, Any]) -> int:
    """
    Validate a simple integer value.
    Clamps to min/max bounds.
    
    Config:
        min: int (default: no minimum)
        max: int (default: no maximum)
        default: int (default: 0)
    """
    default = config.get("default", 0)
    
    # Coerce to int
    if value is None:
        return default
    
    try:
        val = int(value)
    except (ValueError, TypeError):
        return default
    
    # Apply bounds
    min_val = config.get("min")
    max_val = config.get("max")
    
    if min_val is not None:
        val = max(min_val, val)
    if max_val is not None:
        val = min(max_val, val)
    
    return val


def validate_compound(value: Any, config: Dict[str, Any]) -> Dict[str, int]:
    """
    Validate a compound value (score + derived modifier).
    Used for D&D-style attributes where 18 -> +4 modifier.
    
    Config:
        min: int (default: 1)
        max: int (default: 30)
        default: int (default: 10)
        mod_formula: str (default: "floor((score - 10) / 2)")
    
    Returns:
        {"score": int, "mod": int}
    """
    default_score = config.get("default", 10)
    min_val = config.get("min", 1)
    max_val = config.get("max", 30)
    
    # Extract score from input
    if value is None:
        score = default_score
    elif isinstance(value, dict):
        score = value.get("score", value.get("value", default_score))
        try:
            score = int(score)
        except (ValueError, TypeError):
            score = default_score
    elif isinstance(value, (int, float)):
        score = int(value)
    else:
        try:
            score = int(value)
        except (ValueError, TypeError):
            score = default_score
    
    # Clamp score
    score = max(min_val, min(max_val, score))
    
    # Compute modifier (D&D formula by default)
    # Note: In production, this could use the formula engine
    mod = (score - 10) // 2
    
    return {"score": score, "mod": mod}


def validate_step_die(value: Any, config: Dict[str, Any]) -> str:
    """
    Validate a step die value (d4, d6, d8, d10, d12).
    Must be one of the values in the chain.
    
    Config:
        chain: List[str] (default: ["d4", "d6", "d8", "d10", "d12"])
        default: str (default: first in chain)
    """
    chain = config.get("chain", ["d4", "d6", "d8", "d10", "d12"])
    default = config.get("default", chain[0] if chain else "d6")
    
    if value is None:
        return default
    
    # Normalize input
    val_str = str(value).lower().strip()
    
    # Check if in chain (case-insensitive)
    chain_lower = [d.lower() for d in chain]
    if val_str in chain_lower:
        # Return with original casing from chain
        idx = chain_lower.index(val_str)
        return chain[idx]
    
    return default


def validate_ladder(value: Any, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a ladder value (rating with text label).
    Used for Fate-style approaches where +2 = "Fair".
    
    Config:
        min: int (default: -2)
        max: int (default: 6)
        default: int (default: 0)
        labels: Dict[int, str] (default: Fate ladder)
    
    Returns:
        {"value": int, "label": str}
    """
    default_val = config.get("default", 0)
    min_val = config.get("min", -2)
    max_val = config.get("max", 6)
    
    # Default Fate ladder labels
    default_labels = {
        -2: "Terrible",
        -1: "Poor",
        0: "Mediocre",
        1: "Average",
        2: "Fair",
        3: "Good",
        4: "Great",
        5: "Superb",
        6: "Fantastic",
    }
    labels = config.get("labels", default_labels)
    
    # Extract value
    if value is None:
        val = default_val
    elif isinstance(value, dict):
        val = value.get("value", default_val)
        try:
            val = int(val)
        except (ValueError, TypeError):
            val = default_val
    elif isinstance(value, (int, float)):
        val = int(value)
    else:
        try:
            val = int(value)
        except (ValueError, TypeError):
            val = default_val
    
    # Clamp
    val = max(min_val, min(max_val, val))
    
    # Lookup label
    label = labels.get(val, str(val))
    
    return {"value": val, "label": label}


def validate_bool(value: Any, config: Dict[str, Any]) -> bool:
    """
    Validate a boolean value.
    Coerces truthy/falsy values.
    
    Config:
        default: bool (default: False)
    """
    default = config.get("default", False)
    
    if value is None:
        return default
    
    if isinstance(value, bool):
        return value
    
    if isinstance(value, str):
        return value.lower() in ("true", "yes", "1", "on")
    
    if isinstance(value, (int, float)):
        return value != 0
    
    return bool(value)


def validate_text(value: Any, config: Dict[str, Any]) -> str:
    """
    Validate a simple text string.
    
    Config:
        default: str (default: "")
        max_length: int (optional)
        options: List[str] (optional, strict enum)
    """
    default = config.get("default", "")
    
    if value is None:
        return default
        
    val_str = str(value).strip()
    
    # Optional: Enum validation
    options = config.get("options")
    if options and val_str not in options:
        return default
        
    # Optional: Length clamp
    max_len = config.get("max_length")
    if max_len and len(val_str) > max_len:
        val_str = val_str[:max_len]
        
    return val_str


# =============================================================================
# RESOURCE VALIDATORS
# =============================================================================


def validate_pool(value: Any, config: Dict[str, Any]) -> Dict[str, int]:
    """
    Validate a resource pool (current/max pair).
    Ensures current <= max and current >= min.
    
    Config:
        min: int (default: 0)
        default_max: int (default: 10)
    
    Returns:
        {"current": int, "max": int}
    """
    min_val = config.get("min", 0)
    default_max = config.get("default_max", 10)
    
    # Handle various input formats
    if value is None:
        return {"current": default_max, "max": default_max}
    
    if isinstance(value, (int, float)):
        # Single number - treat as both current and max
        val = int(value)
        return {"current": max(min_val, val), "max": val}
    
    if isinstance(value, dict):
        # Extract current and max
        try:
            max_val = int(value.get("max", default_max))
        except (ValueError, TypeError):
            max_val = default_max
        
        try:
            current = int(value.get("current", max_val))
        except (ValueError, TypeError):
            current = max_val
        
        # Clamp current to valid range
        current = max(min_val, min(max_val, current))
        
        return {"current": current, "max": max_val}
    
    return {"current": default_max, "max": default_max}


def validate_counter(value: Any, config: Dict[str, Any]) -> int:
    """
    Validate a simple counter (unbounded or soft-bounded).
    Used for XP, Gold, Fate Points, etc.
    
    Config:
        min: int (default: 0)
        default: int (default: 0)
    """
    min_val = config.get("min", 0)
    default = config.get("default", 0)
    
    if value is None:
        return default
    
    try:
        val = int(value)
    except (ValueError, TypeError):
        return default
    
    return max(min_val, val)


def validate_track(value: Any, config: Dict[str, Any]) -> List[bool]:
    """
    Validate a track (sequential boxes).
    Used for Stress, Death Saves, Wound Levels, etc.
    
    Config:
        length: int (required, default: 3)
    
    Returns:
        List of bools, length = config.length
    """
    length = config.get("length", 3)
    
    if value is None:
        return [False] * length
    
    if isinstance(value, int):
        # Number = count of filled boxes
        filled = max(0, min(length, value))
        return [True] * filled + [False] * (length - filled)
    
    if isinstance(value, list):
        # Ensure correct length and all bools
        result = []
        for i in range(length):
            if i < len(value):
                result.append(bool(value[i]))
            else:
                result.append(False)
        return result
    
    return [False] * length


# =============================================================================
# CONTAINER VALIDATORS
# =============================================================================


def validate_list(value: Any, config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Validate a list container (inventory, abilities, etc.).
    Ensures value is a list, preserves items.
    
    Config:
        (none currently)
    """
    if value is None:
        return []
    
    if isinstance(value, list):
        # Filter to valid items (dicts) and preserve others as simple entries
        result = []
        for item in value:
            if isinstance(item, dict):
                result.append(item)
            elif isinstance(item, str):
                result.append({"name": item})
            # Skip other types
        return result
    
    if isinstance(value, dict):
        # Single item
        return [value]
    
    return []


def validate_tags(value: Any, config: Dict[str, Any]) -> List[str]:
    """
    Validate a tag list (simple string list).
    Used for Languages, Proficiencies, Keywords, etc.
    
    Config:
        (none currently)
    """
    if value is None:
        return []
    
    if isinstance(value, list):
        # Filter to strings only
        return [str(item) for item in value if item is not None]
    
    if isinstance(value, str):
        # Single tag or comma-separated
        if "," in value:
            return [tag.strip() for tag in value.split(",") if tag.strip()]
        return [value] if value.strip() else []
    
    return []


def validate_weighted(value: Any, config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Validate a weighted list (items with weight for encumbrance).
    
    Config:
        capacity_path: str (optional - path to capacity stat for validation hint)
    
    Returns:
        List of items, each guaranteed to have 'weight' field
    """
    if value is None:
        return []
    
    if not isinstance(value, list):
        return []
    
    result = []
    for item in value:
        if isinstance(item, dict):
            # Ensure weight field exists
            if "weight" not in item:
                item = {**item, "weight": 0}
            try:
                item["weight"] = float(item["weight"])
            except (ValueError, TypeError):
                item["weight"] = 0
            result.append(item)
        elif isinstance(item, str):
            result.append({"name": item, "weight": 0})
    
    return result


# =============================================================================
# DEFAULT VALUE GENERATORS
# =============================================================================


def get_default_int(config: Dict[str, Any]) -> int:
    """Get default value for VAL_INT."""
    return config.get("default", 0)


def get_default_compound(config: Dict[str, Any]) -> Dict[str, int]:
    """Get default value for VAL_COMPOUND."""
    return validate_compound(None, config)


def get_default_step_die(config: Dict[str, Any]) -> str:
    """Get default value for VAL_STEP_DIE."""
    chain = config.get("chain", ["d4", "d6", "d8", "d10", "d12"])
    return config.get("default", chain[0] if chain else "d6")


def get_default_ladder(config: Dict[str, Any]) -> Dict[str, Any]:
    """Get default value for VAL_LADDER."""
    return validate_ladder(None, config)


def get_default_bool(config: Dict[str, Any]) -> bool:
    """Get default value for VAL_BOOL."""
    return config.get("default", False)


def get_default_text(config: Dict[str, Any]) -> str:
    """Get default value for VAL_TEXT."""
    return config.get("default", "")


def get_default_pool(config: Dict[str, Any]) -> Dict[str, int]:
    """Get default value for RES_POOL."""
    max_val = config.get("default_max", 10)
    return {"current": max_val, "max": max_val}


def get_default_counter(config: Dict[str, Any]) -> int:
    """Get default value for RES_COUNTER."""
    return config.get("default", 0)


def get_default_track(config: Dict[str, Any]) -> List[bool]:
    """Get default value for RES_TRACK."""
    length = config.get("length", 3)
    return [False] * length


def get_default_list(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get default value for CONT_LIST."""
    return []


def get_default_tags(config: Dict[str, Any]) -> List[str]:
    """Get default value for CONT_TAGS."""
    return []


def get_default_weighted(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get default value for CONT_WEIGHTED."""
    return []
