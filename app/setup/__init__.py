"""
Setup package for game initialization.

Contains:
- ManifestExtractor: Extracts SystemManifest from rules text
- SchemaBuilder: Generates Pydantic models from Manifest
- WorldGenService: Generates world data
- SheetGenerator: Generates character sheets from Manifest
"""

from app.setup.manifest_extractor import ManifestExtractor
from app.setup.schema_builder import SchemaBuilder, InventoryItem
from app.setup.sheet_generator import SheetGenerator
from app.setup.world_gen_service import WorldGenService

__all__ = [
    "ManifestExtractor",
    "SchemaBuilder",
    "InventoryItem",
    "SheetGenerator",
    "WorldGenService",
]
