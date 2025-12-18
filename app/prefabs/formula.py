"""
Formula Evaluation Engine
=========================
Safe evaluation of mathematical formulas for derived stats and constraints.
Uses simpleeval for sandboxed execution.

Supports:
- Arithmetic: +, -, *, /, //, %
- Functions: floor(), ceil(), max(), min(), abs()
- Paths: attributes.str, progression.level (converted to valid identifiers)
- Aliases: str_mod, proficiency (pre-resolved before evaluation)
"""

import logging
import math
import re
from typing import Any, Dict, Optional

from simpleeval import simple_eval

logger = logging.getLogger(__name__)


# =============================================================================
# SAFE FUNCTIONS FOR FORMULAS
# =============================================================================

SAFE_FUNCTIONS = {
    "floor": lambda x: int(math.floor(x)),
    "ceil": lambda x: int(math.ceil(x)),
    "max": max,
    "min": min,
    "abs": abs,
    "round": round,
}


# =============================================================================
# FORMULA EVALUATION
# =============================================================================


def _path_to_identifier(path: str) -> str:
    """
    Convert a dot-path to a valid Python identifier.
    
    Examples:
        "attributes.str" -> "attributes_str"
        "resources.hp.current" -> "resources_hp_current"
    """
    return path.replace(".", "_").replace("-", "_")


def _prepare_formula(formula: str, context_keys: set) -> str:
    """
    Prepare a formula for evaluation by replacing paths with identifiers.
    
    Only replaces paths that exist in the context to avoid breaking
    function names or other valid identifiers.
    """
    result = formula
    
    # Sort by length (longest first) to avoid partial replacements
    sorted_keys = sorted(context_keys, key=len, reverse=True)
    
    for key in sorted_keys:
        if "." in key:
            # This is a path, replace with identifier
            identifier = _path_to_identifier(key)
            # Use word boundaries to avoid partial matches
            pattern = re.escape(key)
            result = re.sub(rf'\b{pattern}\b', identifier, result)
    
    return result


def build_formula_context(
    entity: Dict[str, Any],
    aliases: Optional[Dict[str, str]] = None,
    extra_values: Optional[Dict[str, Any]] = None,
) -> Dict[str, float]:
    """
    Build a flat context dictionary for formula evaluation.
    
    Flattens nested entity structure and resolves aliases.
    
    Args:
        entity: The entity data (nested dict)
        aliases: Formula aliases to resolve (e.g., {"str_mod": "floor((attributes.str - 10) / 2)"})
        extra_values: Additional values to include
    
    Returns:
        Flat dict with all values as floats, keys as valid identifiers
    """
    context: Dict[str, float] = {}
    
    # 1. Flatten entity values
    def flatten(obj: Any, prefix: str = ""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_key = f"{prefix}.{key}" if prefix else key
                flatten(value, new_key)
        elif isinstance(obj, (int, float)):
            # Store with both path and identifier forms
            identifier = _path_to_identifier(prefix)
            context[prefix] = float(obj)
            context[identifier] = float(obj)
        elif isinstance(obj, bool):
            identifier = _path_to_identifier(prefix)
            context[prefix] = 1.0 if obj else 0.0
            context[identifier] = 1.0 if obj else 0.0
        elif isinstance(obj, str):
            # Try to parse as number
            try:
                val = float(obj)
                identifier = _path_to_identifier(prefix)
                context[prefix] = val
                context[identifier] = val
            except ValueError:
                pass
        elif isinstance(obj, list):
            # Store list length
            identifier = _path_to_identifier(prefix)
            context[f"{prefix}.length"] = float(len(obj))
            context[f"{identifier}_length"] = float(len(obj))
    
    flatten(entity)
    
    # 2. Add extra values
    if extra_values:
        for key, value in extra_values.items():
            if isinstance(value, (int, float)):
                identifier = _path_to_identifier(key)
                context[key] = float(value)
                context[identifier] = float(value)
    
    # 3. Resolve aliases (may depend on entity values)
    if aliases:
        # Simple single-pass resolution (no circular dependency handling)
        for alias_name, alias_formula in aliases.items():
            try:
                result = evaluate(alias_formula, context)
                context[alias_name] = result
            except Exception as e:
                logger.debug(f"Failed to resolve alias '{alias_name}': {e}")
                context[alias_name] = 0.0
    
    return context


def evaluate(
    formula: str,
    context: Dict[str, Any],
    default: float = 0.0,
) -> float:
    """
    Safely evaluate a formula string.
    
    Args:
        formula: The formula to evaluate (e.g., "floor((attributes.str - 10) / 2)")
        context: Dictionary of variable values
        default: Value to return on error
    
    Returns:
        Evaluated result as float, or default on any error
    
    Examples:
        >>> evaluate("10 + 5", {})
        15.0
        
        >>> evaluate("floor((score - 10) / 2)", {"score": 18})
        4.0
        
        >>> evaluate("attributes.str + 5", {"attributes.str": 16, "attributes_str": 16})
        21.0
    """
    if not formula or not isinstance(formula, str):
        return default
    
    formula = formula.strip()
    if not formula:
        return default
    
    try:
        # Prepare formula (replace paths with identifiers)
        prepared = _prepare_formula(formula, set(context.keys()))
        
        # Build evaluation context
        eval_context = {}
        for key, value in context.items():
            identifier = _path_to_identifier(key)
            try:
                eval_context[identifier] = float(value) if value is not None else 0.0
            except (ValueError, TypeError):
                eval_context[identifier] = 0.0
        
        # Add safe functions
        eval_context.update(SAFE_FUNCTIONS)
        
        # Evaluate
        result = simple_eval(prepared, names=eval_context)
        
        # Ensure numeric result
        if isinstance(result, bool):
            return 1.0 if result else 0.0
        return float(result)
        
    except Exception as e:
        logger.debug(f"Formula evaluation failed for '{formula}': {e}")
        return default


def evaluate_int(
    formula: str,
    context: Dict[str, Any],
    default: int = 0,
) -> int:
    """
    Evaluate a formula and return an integer result.
    
    Convenience wrapper around evaluate() that converts to int.
    """
    return int(evaluate(formula, context, float(default)))


# =============================================================================
# FORMULA VALIDATION
# =============================================================================


def validate_formula(formula: str, available_paths: set) -> Optional[str]:
    """
    Validate a formula for syntax and path references.
    
    Args:
        formula: The formula to validate
        available_paths: Set of valid paths that can be referenced
    
    Returns:
        Error message if invalid, None if valid
    """
    if not formula or not isinstance(formula, str):
        return None  # Empty formulas are valid (no-op)
    
    # Check for obviously dangerous patterns
    dangerous_patterns = [
        r'__',           # Dunder methods
        r'import',       # Import statements
        r'exec',         # Execution
        r'eval',         # Nested eval
        r'open',         # File operations
        r'lambda',       # Lambda functions
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, formula, re.IGNORECASE):
            return f"Formula contains forbidden pattern: {pattern}"
    
    # Try to parse (will catch syntax errors)
    try:
        # Create dummy context with all paths set to 1
        dummy_context = {path: 1.0 for path in available_paths}
        dummy_context.update({_path_to_identifier(p): 1.0 for p in available_paths})
        dummy_context.update(SAFE_FUNCTIONS)
        
        prepared = _prepare_formula(formula, set(dummy_context.keys()))
        simple_eval(prepared, names=dummy_context)
        
    except Exception as e:
        return f"Formula syntax error: {e}"
    
    return None


def extract_path_references(formula: str) -> set:
    """
    Extract path references from a formula.
    
    Returns set of paths like {"attributes.str", "progression.level"}
    """
    if not formula:
        return set()
    
    # Match patterns like word.word or word.word.word
    pattern = r'\b([a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)*)\b'
    matches = re.findall(pattern, formula, re.IGNORECASE)
    
    # Filter out function names and single words (likely aliases)
    paths = set()
    for match in matches:
        if "." in match and match.lower() not in SAFE_FUNCTIONS:
            paths.add(match)
    
    return paths
