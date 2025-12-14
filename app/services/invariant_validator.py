"""
Invariant Validator
===================
Vocabulary-aware validation engine for game state invariants.

This validator:
1. Uses vocabulary to validate and expand paths
2. Supports wildcards (core_trait.*, resource.*.current)
3. Evaluates expressions using simpleeval
4. Auto-corrects, warns, or rejects based on invariant config

Zero LLM cost at runtime — pure Python validation.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from simpleeval import simple_eval

from app.models.vocabulary import GameVocabulary

logger = logging.getLogger(__name__)


# =============================================================================
# PATH UTILITIES
# =============================================================================

def get_path(data: Dict, path: str) -> Any:
    """
    Navigate a dot-path into a nested dictionary.
    
    Args:
        data: The dictionary to navigate
        path: Dot-separated path like 'resource.hp.current'
        
    Returns:
        The value at the path, or None if not found
    """
    if not path or path in (".", ""):
        return data

    current = data
    for key in path.split("."):
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    return current


def set_path(data: Dict, path: str, value: Any) -> bool:
    """
    Set a value at a dot-path in a nested dictionary.
    Creates intermediate dictionaries as needed.
    
    Args:
        data: The dictionary to modify
        path: Dot-separated path
        value: The value to set
        
    Returns:
        True if successful
    """
    if not path or path in (".", ""):
        return False

    keys = path.split(".")
    current = data

    # Navigate to parent
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
        if not isinstance(current, dict):
            return False

    # Set value
    current[keys[-1]] = value
    return True


def expand_wildcard_paths(data: Dict, pattern: str) -> List[str]:
    """
    Expand a wildcard path pattern against actual data.
    
    Args:
        data: The data dictionary to search
        pattern: Path pattern with wildcards, e.g., 'core_trait.*'
        
    Returns:
        List of matching concrete paths
    """
    if "*" not in pattern:
        return [pattern] if get_path(data, pattern) is not None else []
    
    parts = pattern.split(".")
    results = []
    
    def recurse(current: Any, remaining: List[str], path: List[str]):
        if not remaining:
            results.append(".".join(path))
            return
        
        segment = remaining[0]
        rest = remaining[1:]
        
        if segment == "*":
            if isinstance(current, dict):
                for key in current.keys():
                    recurse(current[key], rest, path + [key])
        else:
            if isinstance(current, dict) and segment in current:
                recurse(current[segment], rest, path + [segment])
    
    recurse(data, parts, [])
    return results


# =============================================================================
# REFERENCE RESOLUTION
# =============================================================================

def resolve_reference(ref: str, entity: Dict) -> Any:
    """
    Resolve a reference string to a concrete value.
    
    Supports:
    - Literal numbers: "0", "-10", "100"
    - Literal floats: "0.5", "1.5"
    - Paths: "resource.hp.max", "core_trait.strength"
    - Expressions: "progression.level + 3", "(core_trait.strength - 10) // 2"
    
    Args:
        ref: The reference string
        entity: The entity data for path/expression resolution
        
    Returns:
        The resolved value, or None if resolution fails
    """
    if ref is None:
        return None
    
    ref = str(ref).strip()
    
    # Try as integer
    try:
        return int(ref)
    except ValueError:
        pass
    
    # Try as float
    try:
        return float(ref)
    except ValueError:
        pass
    
    # Check if it contains operators (expression)
    if any(op in ref for op in ["+", "-", "*", "/", "(", ")", "//"]):
        return _evaluate_expression(ref, entity)
    
    # Treat as simple path
    return get_path(entity, ref)


def _evaluate_expression(expr: str, entity: Dict) -> Any:
    """
    Evaluate a mathematical expression with entity paths as variables.
    
    Args:
        expr: Expression like "progression.level + 3"
        entity: Entity data for variable resolution
        
    Returns:
        Evaluated result, or None on failure
    """
    # Build context from entity paths mentioned in expression
    context = {}
    
    # Extract path-like tokens (sequences of word.word.word)
    tokens = re.findall(r'[a-z_][a-z0-9_.]*', expr, re.IGNORECASE)
    
    modified_expr = expr
    for token in tokens:
        if "." in token:
            val = get_path(entity, token)
            if val is not None:
                # Convert path to valid Python identifier
                var_name = token.replace(".", "_")
                try:
                    context[var_name] = float(val) if isinstance(val, (int, float)) else 0
                except (ValueError, TypeError):
                    context[var_name] = 0
                # Replace in expression
                modified_expr = modified_expr.replace(token, var_name)
    
    try:
        return simple_eval(modified_expr, names=context)
    except Exception as e:
        logger.debug(f"Expression evaluation failed for '{expr}': {e}")
        return None


# =============================================================================
# CONSTRAINT CHECKING
# =============================================================================

def check_violation(
    target: Any, 
    constraint: str, 
    reference: Any, 
    ref_str: str
) -> bool:
    """
    Check if a target value violates a constraint.
    
    Args:
        target: The value being checked
        constraint: The comparison operator
        reference: The resolved reference value
        ref_str: Original reference string (for in_range parsing)
        
    Returns:
        True if the constraint is VIOLATED
    """
    if target is None or reference is None:
        return False
    
    try:
        target_num = float(target)
        ref_num = float(reference)
        
        if constraint == ">=":
            return target_num < ref_num
        elif constraint == "<=":
            return target_num > ref_num
        elif constraint == "==":
            return target_num != ref_num
        elif constraint == "!=":
            return target_num == ref_num
        elif constraint == "in_range":
            # Reference format: "min,max"
            parts = ref_str.split(",")
            if len(parts) == 2:
                lo, hi = float(parts[0].strip()), float(parts[1].strip())
                return target_num < lo or target_num > hi
        elif constraint == "is_one_of":
            # Reference format: "val1,val2,val3"
            allowed = [v.strip() for v in ref_str.split(",")]
            return str(target) not in allowed
            
    except (ValueError, TypeError) as e:
        logger.debug(f"Constraint check failed: {e}")
    
    return False


def calculate_correction(
    target: Any,
    constraint: str,
    reference: Any,
    ref_str: str,
    correction_value: Optional[str],
    entity: Dict,
) -> Any:
    """
    Calculate the corrected value when a constraint is violated.
    
    Args:
        target: The violating value
        constraint: The constraint type
        reference: The resolved reference
        ref_str: Original reference string
        correction_value: Explicit correction value (if provided)
        entity: Entity data for path resolution
        
    Returns:
        The corrected value
    """
    # If explicit correction value provided, use it
    if correction_value:
        resolved = resolve_reference(correction_value, entity)
        if resolved is not None:
            return resolved
    
    # Otherwise, derive from constraint
    try:
        if constraint == ">=":
            return reference  # Clamp to minimum
        elif constraint == "<=":
            return reference  # Clamp to maximum
        elif constraint == "in_range":
            parts = ref_str.split(",")
            if len(parts) == 2:
                lo, hi = float(parts[0].strip()), float(parts[1].strip())
                target_num = float(target)
                if target_num < lo:
                    return lo
                elif target_num > hi:
                    return hi
    except (ValueError, TypeError):
        pass
    
    return reference


# =============================================================================
# MAIN VALIDATOR
# =============================================================================

def validate_entity(
    entity: Dict,
    invariants: List[Any],
    vocabulary: Optional[GameVocabulary] = None,
    auto_correct: bool = True,
) -> Tuple[Dict, List[str], List[str]]:
    """
    Validate an entity against a list of invariants.
    
    Args:
        entity: The entity data dictionary
        invariants: List of StateInvariant objects or dicts
        vocabulary: Optional vocabulary for path validation
        auto_correct: If True, apply corrections for 'clamp' violations
        
    Returns:
        Tuple of:
        - entity: The (possibly corrected) entity
        - corrections: List of correction messages
        - warnings: List of warning messages
    """
    corrections = []
    warnings = []
    
    for inv in invariants:
        # Handle both Pydantic models and dicts
        if hasattr(inv, "model_dump"):
            inv = inv.model_dump()
        elif not isinstance(inv, dict):
            continue
        
        name = inv.get("name", "Unnamed constraint")
        target_pattern = inv.get("target_path")
        constraint = inv.get("constraint")
        ref_str = inv.get("reference")
        on_violation = inv.get("on_violation", "clamp")
        correction_value = inv.get("correction_value")
        
        if not target_pattern or not constraint or ref_str is None:
            continue
        
        # Validate path against vocabulary if provided
        if vocabulary and not vocabulary.validate_path(target_pattern):
            logger.warning(f"Invariant '{name}' has invalid path: {target_pattern}")
            continue
        
        # Expand wildcards to actual paths in entity
        if "*" in target_pattern:
            target_paths = expand_wildcard_paths(entity, target_pattern)
        else:
            target_paths = [target_pattern]
        
        # Check each matching path
        for target_path in target_paths:
            target = get_path(entity, target_path)
            if target is None:
                continue
            
            # Resolve reference
            reference = resolve_reference(ref_str, entity)
            
            # Check for violation
            if check_violation(target, constraint, reference, ref_str):
                if on_violation == "clamp" and auto_correct:
                    new_value = calculate_correction(
                        target, constraint, reference, ref_str, 
                        correction_value, entity
                    )
                    if new_value is not None:
                        # Preserve type
                        if isinstance(target, int) and isinstance(new_value, float):
                            new_value = int(new_value)
                        
                        set_path(entity, target_path, new_value)
                        corrections.append(f"{name}: {target_path} {target} → {new_value}")
                        logger.debug(f"Auto-corrected {target_path}: {target} → {new_value}")
                
                elif on_violation == "flag":
                    warnings.append(f"{name}: {target_path}={target} violates {constraint} {ref_str}")
                    logger.warning(f"Invariant warning: {name}")
                
                elif on_violation == "reject":
                    raise ValueError(
                        f"Invariant violation ({name}): {target_path}={target} "
                        f"violates {constraint} {ref_str}"
                    )
    
    return entity, corrections, warnings


def validate_with_vocabulary(
    entity: Dict,
    invariants: List[Any],
    vocabulary: GameVocabulary,
    auto_correct: bool = True,
) -> Tuple[Dict, List[str], List[str]]:
    """
    Convenience wrapper that requires vocabulary.
    """
    return validate_entity(entity, invariants, vocabulary, auto_correct)


# =============================================================================
# FIELD-LEVEL VALIDATION
# =============================================================================

def validate_field_update(
    entity: Dict,
    path: str,
    new_value: Any,
    vocabulary: Optional[GameVocabulary] = None,
    invariants: Optional[List[Any]] = None,
) -> Tuple[Any, List[str]]:
    """
    Validate a single field update before applying.
    
    This is a lightweight check for individual updates, useful for
    real-time validation in UI or before tool execution.
    
    Args:
        entity: Current entity state
        path: The path being updated
        new_value: The proposed new value
        vocabulary: Optional vocabulary for path validation
        invariants: Optional invariants to check
        
    Returns:
        Tuple of (possibly corrected value, list of messages)
    """
    messages = []
    
    # Validate path
    if vocabulary and not vocabulary.validate_path(path):
        messages.append(f"Invalid path: {path}")
        return new_value, messages
    
    # Create temporary entity with new value
    import copy
    temp_entity = copy.deepcopy(entity)
    set_path(temp_entity, path, new_value)
    
    # Run invariants if provided
    if invariants:
        # Filter to invariants that affect this path
        relevant = []
        for inv in invariants:
            inv_dict = inv.model_dump() if hasattr(inv, "model_dump") else inv
            target = inv_dict.get("target_path", "")
            
            # Check if this invariant is relevant
            if target == path:
                relevant.append(inv)
            elif "*" in target:
                # Check if path matches pattern
                pattern = target.replace(".", r"\.").replace("*", r"[a-z_][a-z0-9_]*")
                if re.match(f"^{pattern}$", path):
                    relevant.append(inv)
        
        if relevant:
            _, corrections, warnings = validate_entity(
                temp_entity, relevant, vocabulary, auto_correct=True
            )
            messages.extend(corrections)
            messages.extend(warnings)
            
            # Get the potentially corrected value
            new_value = get_path(temp_entity, path)
    
    return new_value, messages
