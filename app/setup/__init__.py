"""
Setup package for game initialization.

Contains:
- VocabularyExtractor: Extract game vocabulary from rules text
- SchemaBuilder: Generate Pydantic models from vocabulary
- InvariantExtractor: Extract state invariants with vocabulary validation
- WorldGenService: Generate world data
- SheetGenerator: Generate character sheets
- RulesGenerator: Extract game rules, vocabulary, and procedures
"""

from app.setup.vocabulary_extractor import (
    VocabularyExtractor,
    extract_vocabulary_from_text,
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
from app.setup.invariant_extractor import (
    InvariantExtractor,
    extract_invariants_with_vocabulary,
)
from app.setup.rules_generator import RulesGenerator

__all__ = [
    # Vocabulary
    "VocabularyExtractor",
    "extract_vocabulary_from_text",
    # Schema Builder
    "SchemaBuilder",
    "PoolValue",
    "LadderValue",
    "TagValue",
    "InventoryItem",
    "build_character_model_from_vocabulary",
    "build_creation_model_from_vocabulary",
    "get_creation_hints_from_vocabulary",
    # Invariants
    "InvariantExtractor",
    "extract_invariants_with_vocabulary",
    # Rules
    "RulesGenerator",
]
