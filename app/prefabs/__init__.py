"""
Prefabs Package
===============
Pre-defined building blocks for TTRPG character sheet fields.

Each prefab bundles:
- Data shape (vocabulary)
- Validator (invariants)
- Widget hint (rendering)
- AI hint (prompt context)

Also includes manifest structures and validation pipeline.
"""

from app.prefabs.formula import (
    build_formula_context,
    evaluate,
    evaluate_int,
    extract_path_references,
    validate_formula,
)
from app.prefabs.manifest import (
    VALID_CATEGORIES,
    EngineConfig,
    FieldDef,
    SystemManifest,
    create_empty_manifest,
    merge_manifests,
    validate_manifest,
)
from app.prefabs.registry import (
    PREFABS,
    Prefab,
    get_ai_hints,
    get_default_value,
    get_prefab,
    list_prefabs,
    validate_value,
)
from app.prefabs.validation import get_path, set_path, validate_entity
from app.prefabs.validators import (
    validate_bool,
    validate_compound,
    validate_counter,
    validate_int,
    validate_ladder,
    validate_list,
    validate_pool,
    validate_step_die,
    validate_tags,
    validate_track,
    validate_weighted,
)

__all__ = [
    "PREFABS",
    "VALID_CATEGORIES",
    "EngineConfig",
    # Manifest structures
    "FieldDef",
    # Core prefabs
    "Prefab",
    "SystemManifest",
    "build_formula_context",
    "create_empty_manifest",
    # Formula evaluation
    "evaluate",
    "evaluate_int",
    "extract_path_references",
    "get_ai_hints",
    "get_default_value",
    "get_path",
    # Prefab functions
    "get_prefab",
    "list_prefabs",
    "merge_manifests",
    "set_path",
    "validate_bool",
    "validate_compound",
    "validate_counter",
    # Validation Pipeline
    "validate_entity",
    "validate_formula",
    # Validators
    "validate_int",
    "validate_ladder",
    "validate_list",
    # Manifest utilities
    "validate_manifest",
    "validate_pool",
    "validate_step_die",
    "validate_tags",
    "validate_track",
    "validate_value",
    "validate_weighted",
]
