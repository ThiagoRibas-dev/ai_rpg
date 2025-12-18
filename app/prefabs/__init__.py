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

from app.prefabs.registry import (
    Prefab,
    PREFABS,
    get_prefab,
    list_prefabs,
    validate_value,
    get_default_value,
    get_ai_hints,
)

from app.prefabs.validators import (
    validate_int,
    validate_compound,
    validate_step_die,
    validate_ladder,
    validate_bool,
    validate_pool,
    validate_counter,
    validate_track,
    validate_list,
    validate_tags,
    validate_weighted,
)

from app.prefabs.manifest import (
    FieldDef,
    EngineConfig,
    SystemManifest,
    VALID_CATEGORIES,
    validate_manifest,
    merge_manifests,
    create_empty_manifest,
)

from app.prefabs.formula import (
    evaluate,
    evaluate_int,
    build_formula_context,
    validate_formula,
    extract_path_references,
)

from app.prefabs.validation import (
    validate_entity,
    get_path,
    set_path
)

__all__ = [
    # Core prefabs
    "Prefab",
    "PREFABS",
    
    # Prefab functions
    "get_prefab",
    "list_prefabs", 
    "validate_value",
    "get_default_value",
    "get_ai_hints",
    
    # Validators
    "validate_int",
    "validate_compound",
    "validate_step_die",
    "validate_ladder",
    "validate_bool",
    "validate_pool",
    "validate_counter",
    "validate_track",
    "validate_list",
    "validate_tags",
    "validate_weighted",
    
    # Manifest structures
    "FieldDef",
    "EngineConfig",
    "SystemManifest",
    "VALID_CATEGORIES",
    
    # Manifest utilities
    "validate_manifest",
    "merge_manifests",
    "create_empty_manifest",
    
    # Formula evaluation
    "evaluate",
    "evaluate_int",
    "build_formula_context",
    "validate_formula",
    "extract_path_references",
    
    # Validation Pipeline
    "validate_entity",
    "get_path",
    "set_path"
]
