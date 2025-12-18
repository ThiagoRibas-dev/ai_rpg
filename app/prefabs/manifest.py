"""
Manifest Data Structures
========================
Defines the core dataclasses for system manifests:
- FieldDef: Single field definition with prefab binding
- EngineConfig: Resolution mechanics (prompt context)
- SystemManifest: Complete game system definition

A manifest is the complete definition of a TTRPG system's character sheet
structure, validation rules, and gameplay procedures.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.prefabs.registry import PREFABS
from app.prefabs.formula import validate_formula

logger = logging.getLogger(__name__)


# =============================================================================
# VALID CATEGORIES
# =============================================================================

VALID_CATEGORIES = {
    "identity",      # Name, description, background
    "attributes",    # Core stats (STR, DEX, etc.)
    "skills",        # Learned capabilities
    "resources",     # HP, Mana, Stress, etc.
    "features",      # Feats, abilities, powers
    "inventory",     # Equipment, items
    "progression",   # XP, Level, advancement
    "status",        # Conditions, temporary states
    "combat",        # AC, Initiative, attack bonuses
    "connections",   # NPCs, factions, relationships
    "narrative",     # Aspects, beliefs, bonds
}


# =============================================================================
# FIELD DEFINITION
# =============================================================================


@dataclass
class FieldDef:
    """
    Definition of a single field in the character sheet.
    
    Attributes:
        path: Dot-path identifier (e.g., "resources.hp")
        label: Human-readable display name
        prefab: Prefab type ID (e.g., "RES_POOL")
        category: Grouping category for UI organization
        config: Prefab-specific configuration (min, max, length, etc.)
        formula: Formula for derived fields (read-only value)
        max_formula: Formula for computing max of RES_POOL fields
        default_formula: Formula for initial value
        threshold_hint: AI hint for threshold triggers (e.g., "At 0: unconscious")
        usage_hint: AI hint for how to use this field
    """
    path: str
    label: str
    prefab: str
    category: str
    config: Dict[str, Any] = field(default_factory=dict)
    formula: Optional[str] = None
    max_formula: Optional[str] = None
    default_formula: Optional[str] = None
    threshold_hint: Optional[str] = None
    usage_hint: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "path": self.path,
            "label": self.label,
            "prefab": self.prefab,
            "category": self.category,
        }
        
        # Only include non-empty optional fields
        if self.config:
            result["config"] = self.config
        if self.formula:
            result["formula"] = self.formula
        if self.max_formula:
            result["max_formula"] = self.max_formula
        if self.default_formula:
            result["default_formula"] = self.default_formula
        if self.threshold_hint:
            result["threshold_hint"] = self.threshold_hint
        if self.usage_hint:
            result["usage_hint"] = self.usage_hint
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FieldDef":
        """Create from dictionary."""
        return cls(
            path=data["path"],
            label=data["label"],
            prefab=data["prefab"],
            category=data["category"],
            config=data.get("config", {}),
            formula=data.get("formula"),
            max_formula=data.get("max_formula"),
            default_formula=data.get("default_formula"),
            threshold_hint=data.get("threshold_hint"),
            usage_hint=data.get("usage_hint"),
        )


# =============================================================================
# ENGINE CONFIGURATION
# =============================================================================


@dataclass
class EngineConfig:
    """
    Core resolution mechanics for the game system.
    
    This is injected into prompts so the AI knows how to resolve actions.
    
    Attributes:
        dice: Primary dice notation (e.g., "1d20", "2d6", "d100")
        mechanic: Description of roll mechanics
        success: How success is determined
        crit: Critical success rules
        fumble: Critical failure rules (optional)
    """
    dice: str
    mechanic: str
    success: str
    crit: str
    fumble: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "dice": self.dice,
            "mechanic": self.mechanic,
            "success": self.success,
            "crit": self.crit,
        }
        if self.fumble:
            result["fumble"] = self.fumble
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EngineConfig":
        """Create from dictionary."""
        return cls(
            dice=data.get("dice", "1d20"),
            mechanic=data.get("mechanic", "Roll + modifier vs target"),
            success=data.get("success", "Meet or beat target"),
            crit=data.get("crit", ""),
            fumble=data.get("fumble", ""),
        )
    
    def to_prompt_text(self) -> str:
        """Generate text for injection into AI prompts."""
        lines = [
            f"**Dice:** {self.dice}",
            f"**Mechanic:** {self.mechanic}",
            f"**Success:** {self.success}",
        ]
        if self.crit:
            lines.append(f"**Critical:** {self.crit}")
        if self.fumble:
            lines.append(f"**Fumble:** {self.fumble}")
        
        return "\n".join(lines)


# =============================================================================
# SYSTEM MANIFEST
# =============================================================================


@dataclass
class SystemManifest:
    """
    Complete definition of a TTRPG game system.
    
    A manifest contains everything needed to:
    - Validate character data (via prefabs)
    - Compute derived values (via formulas)
    - Generate AI context (via engine, procedures, hints)
    
    Attributes:
        id: Unique system identifier (e.g., "dnd_5e")
        name: Human-readable name (e.g., "D&D 5th Edition")
        engine: Resolution mechanics configuration
        procedures: Text procedures by game mode
        fields: List of field definitions
        aliases: Formula shortcuts (e.g., {"str_mod": "floor((attributes.str - 10) / 2)"})
    """
    id: str
    name: str
    engine: EngineConfig
    procedures: Dict[str, str] = field(default_factory=dict)
    fields: List[FieldDef] = field(default_factory=list)
    aliases: Dict[str, str] = field(default_factory=dict)
    
    # -------------------------------------------------------------------------
    # Field Access
    # -------------------------------------------------------------------------
    
    def get_field(self, path: str) -> Optional[FieldDef]:
        """Get a field definition by path."""
        for f in self.fields:
            if f.path == path:
                return f
        return None
    
    def get_fields_by_category(self, category: str) -> List[FieldDef]:
        """Get all fields in a category."""
        return [f for f in self.fields if f.category == category]
    
    def get_fields_by_prefab(self, prefab: str) -> List[FieldDef]:
        """Get all fields using a specific prefab type."""
        return [f for f in self.fields if f.prefab == prefab]
    
    def get_all_paths(self) -> List[str]:
        """Get all field paths."""
        return [f.path for f in self.fields]
    
    def get_categories(self) -> List[str]:
        """Get list of categories that have fields."""
        return sorted(set(f.category for f in self.fields))
    
    # -------------------------------------------------------------------------
    # Context Generation
    # -------------------------------------------------------------------------
    
    def get_path_hints(self) -> str:
        """
        Generate path hints for AI context.
        
        Returns text like:
            **Resources:**
              `resources.hp.current` - Hit Points (current/max pool)
              `resources.stress` - Stress (9 boxes, mark to fill)
        """
        lines = ["## VALID PATHS"]
        
        for category in self.get_categories():
            fields = self.get_fields_by_category(category)
            if not fields:
                continue
            
            lines.append(f"\n**{category.title()}:**")
            
            for f in fields:
                prefab = PREFABS.get(f.prefab)
                hint = prefab.ai_hint if prefab else ""
                
                # For pools, indicate the .current subpath
                if f.prefab == "RES_POOL":
                    lines.append(f"  `{f.path}.current` - {f.label} ({hint})")
                else:
                    lines.append(f"  `{f.path}` - {f.label} ({hint})")
        
        return "\n".join(lines)
    
    def get_procedure(self, mode: str) -> Optional[str]:
        """Get procedure text for a game mode."""
        return self.procedures.get(mode.lower())
    
    def get_engine_text(self) -> str:
        """Get engine description for prompts."""
        return self.engine.to_prompt_text()
    
    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "engine": self.engine.to_dict(),
            "procedures": self.procedures,
            "fields": [f.to_dict() for f in self.fields],
            "aliases": self.aliases,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SystemManifest":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            engine=EngineConfig.from_dict(data.get("engine", {})),
            procedures=data.get("procedures", {}),
            fields=[FieldDef.from_dict(f) for f in data.get("fields", [])],
            aliases=data.get("aliases", {}),
        )
    
    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
    
    @classmethod
    def from_json(cls, json_str: str) -> "SystemManifest":
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    @classmethod
    def from_file(cls, path: Path) -> "SystemManifest":
        """Load from JSON file."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def to_file(self, path: Path):
        """Save to JSON file."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2)


# =============================================================================
# MANIFEST VALIDATION
# =============================================================================


def validate_manifest(manifest: SystemManifest) -> List[str]:
    """
    Validate a manifest for correctness.
    
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    # 1. Check required fields
    if not manifest.id:
        errors.append("Manifest missing 'id'")
    if not manifest.name:
        errors.append("Manifest missing 'name'")
    
    # 2. Validate each field
    seen_paths = set()
    all_paths = set()
    
    for f in manifest.fields:
        # Check for duplicate paths
        if f.path in seen_paths:
            errors.append(f"Duplicate field path: {f.path}")
        seen_paths.add(f.path)
        all_paths.add(f.path)
        
        # Add subpaths for pools
        if f.prefab == "RES_POOL":
            all_paths.add(f"{f.path}.current")
            all_paths.add(f"{f.path}.max")
        
        # Check prefab exists
        if f.prefab not in PREFABS:
            errors.append(f"Field '{f.path}' uses unknown prefab: {f.prefab}")
        
        # Check category is valid
        if f.category not in VALID_CATEGORIES:
            errors.append(f"Field '{f.path}' uses unknown category: {f.category}")
        
        # Check required config for specific prefabs
        if f.prefab == "RES_TRACK" and "length" not in f.config:
            errors.append(f"Field '{f.path}' (RES_TRACK) missing 'length' config")
    
    # 3. Add alias names to available paths
    all_paths.update(manifest.aliases.keys())
    
    # 4. Validate formulas
    for f in manifest.fields:
        for formula_name, formula in [
            ("formula", f.formula),
            ("max_formula", f.max_formula),
            ("default_formula", f.default_formula),
        ]:
            if formula:
                error = validate_formula(formula, all_paths)
                if error:
                    errors.append(f"Field '{f.path}' {formula_name}: {error}")
    
    # 5. Validate aliases
    for alias_name, alias_formula in manifest.aliases.items():
        error = validate_formula(alias_formula, all_paths)
        if error:
            errors.append(f"Alias '{alias_name}': {error}")
    
    return errors


# =============================================================================
# MANIFEST UTILITIES
# =============================================================================


def merge_manifests(base: SystemManifest, override: SystemManifest) -> SystemManifest:
    """
    Merge two manifests, with override taking precedence.
    
    Useful for extending a base system with house rules.
    """
    # Start with base
    merged_fields = {f.path: f for f in base.fields}
    
    # Override with new fields
    for f in override.fields:
        merged_fields[f.path] = f
    
    return SystemManifest(
        id=override.id or base.id,
        name=override.name or base.name,
        engine=override.engine if override.engine.dice else base.engine,
        procedures={**base.procedures, **override.procedures},
        fields=list(merged_fields.values()),
        aliases={**base.aliases, **override.aliases},
    )


def create_empty_manifest(system_id: str, system_name: str) -> SystemManifest:
    """Create a minimal empty manifest."""
    return SystemManifest(
        id=system_id,
        name=system_name,
        engine=EngineConfig(
            dice="1d20",
            mechanic="Roll + modifier vs target",
            success="Meet or beat target",
            crit="",
            fumble="",
        ),
        procedures={},
        fields=[],
        aliases={},
    )
