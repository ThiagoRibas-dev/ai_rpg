"""
Setup package for game initialization.

Contains:
- VocabularyExtractor: Role-scoped vocabulary extraction
- InvariantExtractor: Structural + edge case invariants
- SchemaBuilder: Generate Pydantic models from vocabulary
- WorldGenService: Generate world data
- SheetGenerator: Generate character sheets
- RulesGenerator: Orchestrate full extraction pipeline
"""

from app.setup.vocabulary_extractor import (
    VocabularyExtractor,
)
from app.setup.invariant_extractor import (
    InvariantExtractor,
    generate_structural_invariants,
    extract_invariants,
)
from app.setup.schema_builder import (
    SchemaBuilder,
    PoolValue,
    LadderValue,
    TagValue,
    InventoryItem,
    build_character_model_from_vocabulary,
    build_creation_model_from_vocabulary,
    get_creation_hints_from_vocabulary,
)
from app.setup.rules_generator import RulesGenerator

__all__ = [
    # Vocabulary
    "VocabularyExtractor",
    # Invariants
    "InvariantExtractor",
    "generate_structural_invariants",
    "extract_invariants",
    # Schema Builder
    "SchemaBuilder",
    "PoolValue",
    "LadderValue",
    "TagValue",
    "InventoryItem",
    "build_character_model_from_vocabulary",
    "build_creation_model_from_vocabulary",
    "get_creation_hints_from_vocabulary",
    # Rules
    "RulesGenerator",
]
