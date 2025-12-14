"""
Game Vocabulary System
======================
The single source of truth for game system definitions.

This module defines the "building blocks" of any TTRPG system in a way that's
flexible enough to represent D&D, Fate, Kids on Bikes, PbtA, and anything else.

Key Concepts:
- FieldType: HOW data is stored (number, pool, track, die, ladder, tag, text, list)
- SemanticRole: WHAT the data means (core_trait, resource, capability, status, etc.)
- FieldDefinition: A single field combining type + role + metadata
- GameVocabulary: The complete vocabulary for a game system

All paths, schemas, invariants, and tool hints are derived from the vocabulary.
"""

from enum import Enum
from functools import cached_property
from typing import Any, Dict, List, Optional, Union
import re
import logging

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS: The Two Dimensions
# =============================================================================

class FieldType(str, Enum):
    """
    HOW the data is stored and displayed.
    
    This defines the structural representation of a value.
    """
    NUMBER = "number"        # Simple integer or float: 10, 15, -2, 3.5
    POOL = "pool"            # Current/Max pair: {"current": 5, "max": 10}
    TRACK = "track"          # Checkbox array: [True, True, False, False]
    DIE = "die"              # Die notation string: "d8", "2d6", "d12"
    LADDER = "ladder"        # Named rating: {"value": 2, "label": "Good"}
    TAG = "tag"              # Narrative tag with optional weight: {"text": "High Concept", "free_invokes": 1}
    TEXT = "text"            # Free-form text string
    LIST = "list"            # Array of items (inventory, abilities, etc.)


class SemanticRole(str, Enum):
    """
    WHAT the field means in the game.
    
    This defines the semantic purpose of a value, regardless of how it's stored.
    """
    CORE_TRAIT = "core_trait"      # Primary character stats (STR, DEX, Approaches, Stats)
    RESOURCE = "resource"          # Depletable values (HP, Stress, Fate Points, Mana)
    CAPABILITY = "capability"      # Skills, abilities, moves, proficiencies
    STATUS = "status"              # Temporary conditions, tags, states
    ASPECT = "aspect"              # Narrative truths (Fate Aspects, Beliefs, Instincts)
    PROGRESSION = "progression"    # XP, level, advancements, milestones
    EQUIPMENT = "equipment"        # Gear, inventory, possessions
    CONNECTION = "connection"      # Relationships, bonds, contacts
    META = "meta"                  # System metadata (not character data)


# =============================================================================
# FIELD DEFINITION
# =============================================================================

class FieldDefinition(BaseModel):
    """
    A single field in the game vocabulary.
    
    Combines semantic meaning (what it represents) with structural storage (how it's stored).
    Includes all metadata needed for validation, display, and derivation.
    
    Examples:
    - D&D Strength: NUMBER field with CORE_TRAIT role
    - Fate Stress: TRACK field with RESOURCE role  
    - Kids on Bikes Brains: DIE field with CORE_TRAIT role
    - Fate Aspect: TAG field with ASPECT role
    """
    
    # === Identity ===
    key: str = Field(
        ..., 
        description="Unique snake_case identifier within its role category",
        pattern=r"^[a-z][a-z0-9_]*$"
    )
    label: str = Field(
        ..., 
        description="Human-readable display name"
    )
    description: str = Field(
        "", 
        description="Explanation for prompts and UI tooltips"
    )
    
    # === The Two Dimensions ===
    semantic_role: SemanticRole = Field(
        ...,
        description="What this field represents in the game"
    )
    field_type: FieldType = Field(
        ...,
        description="How the data is stored and displayed"
    )
    
    # === Type-Specific Configuration ===
    # Use the fields that apply to your field_type
    
    # For NUMBER, POOL, TRACK, LADDER
    default_value: Optional[Any] = Field(
        None,
        description="Default value when creating new entities"
    )
    min_value: Optional[Union[int, float]] = Field(
        None,
        description="Minimum allowed value (for NUMBER, POOL.current)"
    )
    max_value: Optional[Union[int, float]] = Field(
        None,
        description="Maximum allowed value (for NUMBER, POOL.current, LADDER)"
    )
    
    # For POOL
    max_source: Optional[str] = Field(
        None,
        description="Path or formula for max value, e.g., 'core_trait.constitution' or '10 + level'"
    )
    
    # For TRACK
    track_length: Optional[int] = Field(
        None,
        description="Number of boxes in the track"
    )
    
    # For DIE
    die_default: Optional[str] = Field(
        None,
        description="Default die notation, e.g., 'd8'"
    )
    
    # For LADDER
    ladder_labels: Optional[Dict[int, str]] = Field(
        None,
        description="Mapping of values to labels, e.g., {2: 'Fair', 3: 'Good', 4: 'Great'}"
    )
    
    # For derived values
    formula: Optional[str] = Field(
        None,
        description="Formula to calculate this value, e.g., '(core_trait.strength - 10) // 2'"
    )
    is_derived: bool = Field(
        False,
        description="If True, this value is calculated from other values"
    )
    
    # For capabilities/skills
    governing_trait: Optional[str] = Field(
        None,
        description="Key of the core_trait that governs this capability"
    )
    requires_training: bool = Field(
        False,
        description="If True, this capability requires explicit training to use"
    )
    
    # === Validation Hints ===
    can_go_negative: bool = Field(
        False,
        description="If True, value can go below 0 (e.g., D&D HP can go to -10)"
    )
    clamp_to_max: bool = Field(
        True,
        description="If True, automatically clamp value to max when exceeded"
    )
    
    # === Display Hints ===
    icon: Optional[str] = Field(
        None,
        description="Icon identifier for UI display"
    )
    color: Optional[str] = Field(
        None,
        description="Color hint for UI display"
    )
    hidden: bool = Field(
        False,
        description="If True, hide from standard UI display"
    )
    
    def get_sub_paths(self) -> List[str]:
        """
        Get the sub-paths for this field based on its type.
        
        Returns paths relative to the field, e.g., ["current", "max"] for POOL.
        """
        if self.field_type == FieldType.POOL:
            return ["current", "max"]
        elif self.field_type == FieldType.TRACK:
            length = self.track_length or 4
            return [str(i) for i in range(length)] + ["filled"]
        elif self.field_type == FieldType.LADDER:
            return ["value", "label"]
        elif self.field_type == FieldType.TAG:
            return ["text", "free_invokes"]
        else:
            return []


# =============================================================================
# GAME VOCABULARY
# =============================================================================

class GameVocabulary(BaseModel):
    """
    Complete vocabulary for a game system.
    
    This is the SINGLE SOURCE OF TRUTH for:
    - What fields exist in this system
    - How those fields are structured
    - What paths are valid for entity updates
    - What invariants can reference
    
    All schemas, validators, and tool hints derive from this vocabulary.
    """
    
    # === System Metadata ===
    system_name: str = Field(
        ...,
        description="Name of the game system, e.g., 'Dungeons & Dragons 5th Edition'"
    )
    system_id: str = Field(
        "",
        description="Unique snake_case identifier for the system"
    )
    genre: str = Field(
        "fantasy",
        description="Primary genre of the system"
    )
    version: str = Field(
        "1.0",
        description="Version of this vocabulary definition"
    )
    
    # === Resolution Mechanics ===
    dice_notation: str = Field(
        "d20",
        description="Primary dice used by the system"
    )
    resolution_mechanic: str = Field(
        "",
        description="How rolls are resolved, e.g., 'Roll + Mod vs DC'"
    )
    
    # === The Fields ===
    fields: Dict[str, FieldDefinition] = Field(
        default_factory=dict,
        description="All field definitions, keyed by unique identifier"
    )
    
    # === System-Specific Terminology ===
    terminology: Dict[str, str] = Field(
        default_factory=dict,
        description="System-specific terms, e.g., {'damage': 'Harm', 'health': 'Stress'}"
    )
    
    # === Validation ===
    
    def add_field(self, field: FieldDefinition) -> None:
        """Add a field to the vocabulary."""
        full_key = f"{field.semantic_role.value}.{field.key}"
        self.fields[full_key] = field
        # Clear cached properties
        if "valid_paths" in self.__dict__:
            del self.__dict__["valid_paths"]
        if "valid_path_patterns" in self.__dict__:
            del self.__dict__["valid_path_patterns"]
    
    @cached_property
    def valid_paths(self) -> List[str]:
        """
        All valid dot-paths for entity data in this system.
        
        These are the paths that can be used in:
        - entity.update tool calls
        - State invariant definitions
        - Context queries
        """
        paths = []
        
        for full_key, field in self.fields.items():
            # Base path is role.key
            base_path = full_key
            
            # Add sub-paths based on field type
            sub_paths = field.get_sub_paths()
            if sub_paths:
                for sub in sub_paths:
                    paths.append(f"{base_path}.{sub}")
            else:
                paths.append(base_path)
        
        # Standard paths present in ALL systems
        paths.extend([
            "identity.name",
            "identity.description",
            "identity.concept",
            "identity.player_name",
        ])
        
        return sorted(set(paths))
    
    @cached_property
    def valid_path_patterns(self) -> List[str]:
        """
        Regex patterns for wildcard matching of paths.
        
        Used when validating invariants that use wildcards like "core_trait.*"
        """
        patterns = set()
        
        # Build patterns from semantic roles that have fields
        roles_with_fields = set()
        for full_key in self.fields.keys():
            role = full_key.split(".")[0]
            roles_with_fields.add(role)
        
        for role in roles_with_fields:
            patterns.add(rf"{role}\.[a-z_][a-z0-9_]*")
            patterns.add(rf"{role}\.[a-z_][a-z0-9_]*\.[a-z_][a-z0-9_]*")
        
        return list(patterns)
    
    def validate_path(self, path: str) -> bool:
        """
        Check if a path is valid for this vocabulary.
        
        Supports:
        - Exact paths: "resource.hp.current"
        - Wildcards: "core_trait.*", "resource.*.current"
        
        Returns True if the path is valid or matches a valid pattern.
        """
        # Normalize path
        path = path.strip().lower()
        
        # Direct match
        if path in self.valid_paths:
            return True
        
        # Wildcard expansion
        if "*" in path:
            # Convert wildcard to regex
            regex_pattern = path.replace(".", r"\.").replace("*", r"[a-z_][a-z0-9_]*")
            try:
                pattern = re.compile(f"^{regex_pattern}$")
                return any(pattern.match(p) for p in self.valid_paths)
            except re.error:
                logger.warning(f"Invalid path pattern: {path}")
                return False
        
        # Pattern match (for dynamically named fields)
        for pattern in self.valid_path_patterns:
            try:
                if re.match(f"^{pattern}$", path):
                    return True
            except re.error:
                continue
        
        return False
    
    def expand_wildcard_path(self, path: str) -> List[str]:
        """
        Expand a wildcard path into all matching concrete paths.
        
        Example: "core_trait.*" -> ["core_trait.strength", "core_trait.dexterity", ...]
        """
        if "*" not in path:
            return [path] if self.validate_path(path) else []
        
        regex_pattern = path.replace(".", r"\.").replace("*", r"[a-z_][a-z0-9_]*")
        try:
            pattern = re.compile(f"^{regex_pattern}$")
            return [p for p in self.valid_paths if pattern.match(p)]
        except re.error:
            return []
    
    # === Query Methods ===
    
    def get_fields_by_role(self, role: SemanticRole) -> Dict[str, FieldDefinition]:
        """Get all fields with a specific semantic role."""
        prefix = f"{role.value}."
        return {
            k.replace(prefix, ""): v 
            for k, v in self.fields.items() 
            if k.startswith(prefix)
        }
    
    def get_fields_by_type(self, field_type: FieldType) -> Dict[str, FieldDefinition]:
        """Get all fields with a specific field type."""
        return {k: v for k, v in self.fields.items() if v.field_type == field_type}
    
    def get_field(self, role: SemanticRole, key: str) -> Optional[FieldDefinition]:
        """Get a specific field by role and key."""
        full_key = f"{role.value}.{key}"
        return self.fields.get(full_key)
    
    def get_field_by_path(self, path: str) -> Optional[FieldDefinition]:
        """Get the field definition for a given path."""
        # Strip sub-paths to get the field key
        parts = path.split(".")
        if len(parts) >= 2:
            base_key = f"{parts[0]}.{parts[1]}"
            return self.fields.get(base_key)
        return None
    
    # === Prompt Generation ===
    
    def get_path_hints_for_prompt(self, include_descriptions: bool = False) -> str:
        """
        Generate a prompt-friendly description of valid paths.
        
        Used to guide the LLM when it needs to reference or update entity data.
        """
        lines = ["## Valid Entity Paths for This System\n"]
        
        # Group by semantic role
        for role in SemanticRole:
            role_fields = self.get_fields_by_role(role)
            if not role_fields:
                continue
            
            lines.append(f"**{role.value.replace('_', ' ').title()}:**")
            
            for key, field in role_fields.items():
                base_path = f"{role.value}.{key}"
                sub_paths = field.get_sub_paths()
                
                if sub_paths:
                    sub_str = ", ".join(f".{s}" for s in sub_paths[:3])
                    if len(sub_paths) > 3:
                        sub_str += ", ..."
                    path_display = f"`{base_path}` ({sub_str})"
                else:
                    path_display = f"`{base_path}`"
                
                if include_descriptions and field.description:
                    lines.append(f"  - {path_display}: {field.description}")
                else:
                    lines.append(f"  - {path_display}")
            
            lines.append("")  # Blank line between roles
        
        return "\n".join(lines)
    
    def get_field_hints_for_prompt(self, role: Optional[SemanticRole] = None) -> str:
        """
        Generate detailed field hints for character creation prompts.
        
        Includes type, ranges, and semantic information.
        """
        lines = []
        
        fields_to_describe = (
            self.get_fields_by_role(role) if role 
            else {k: v for k, v in self.fields.items()}
        )
        
        for full_key, field in fields_to_describe.items():
            type_hint = self._get_type_hint(field)
            range_hint = self._get_range_hint(field)
            
            parts = [f"- **{field.label}** (`{full_key}`)"]
            parts.append(f"  Type: {type_hint}")
            if range_hint:
                parts.append(f"  Range: {range_hint}")
            if field.description:
                parts.append(f"  Info: {field.description}")
            if field.governing_trait:
                parts.append(f"  Governed by: {field.governing_trait}")
            
            lines.append("\n".join(parts))
        
        return "\n\n".join(lines)
    
    def _get_type_hint(self, field: FieldDefinition) -> str:
        """Get a human-readable type hint for a field."""
        type_hints = {
            FieldType.NUMBER: "integer value",
            FieldType.POOL: "pool with current/max",
            FieldType.TRACK: f"track with {field.track_length or 4} boxes",
            FieldType.DIE: f"die type (e.g., {field.die_default or 'd8'})",
            FieldType.LADDER: "rating on a ladder",
            FieldType.TAG: "narrative tag/aspect",
            FieldType.TEXT: "free-form text",
            FieldType.LIST: "list of items",
        }
        return type_hints.get(field.field_type, "value")
    
    def _get_range_hint(self, field: FieldDefinition) -> str:
        """Get a human-readable range hint for a field."""
        parts = []
        if field.min_value is not None:
            parts.append(f"min {field.min_value}")
        if field.max_value is not None:
            parts.append(f"max {field.max_value}")
        if field.ladder_labels:
            labels = [f"{v}={k}" for k, v in sorted(field.ladder_labels.items())]
            parts.append(f"labels: {', '.join(labels[:4])}")
        return ", ".join(parts) if parts else ""
    
    # === Export / Import ===
    
    def to_summary_dict(self) -> Dict[str, Any]:
        """Export a summary for debugging/logging."""
        role_counts = {}
        for full_key in self.fields.keys():
            role = full_key.split(".")[0]
            role_counts[role] = role_counts.get(role, 0) + 1
        
        return {
            "system_name": self.system_name,
            "total_fields": len(self.fields),
            "fields_by_role": role_counts,
            "total_paths": len(self.valid_paths),
            "dice": self.dice_notation,
        }


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_dnd_like_vocabulary(system_name: str = "D&D 5e") -> GameVocabulary:
    """
    Create a vocabulary for D&D-like systems.
    
    Useful for testing or as a fallback when extraction fails.
    """
    vocab = GameVocabulary(
        system_name=system_name,
        system_id=system_name.lower().replace(" ", "_"),
        genre="fantasy",
        dice_notation="d20",
        resolution_mechanic="d20 + modifier vs DC",
    )
    
    # Core traits (ability scores)
    for key, label in [
        ("strength", "Strength"),
        ("dexterity", "Dexterity"),
        ("constitution", "Constitution"),
        ("intelligence", "Intelligence"),
        ("wisdom", "Wisdom"),
        ("charisma", "Charisma"),
    ]:
        vocab.add_field(FieldDefinition(
            key=key,
            label=label,
            semantic_role=SemanticRole.CORE_TRAIT,
            field_type=FieldType.NUMBER,
            default_value=10,
            min_value=1,
            max_value=30,
        ))
    
    # Resources
    vocab.add_field(FieldDefinition(
        key="hp",
        label="Hit Points",
        semantic_role=SemanticRole.RESOURCE,
        field_type=FieldType.POOL,
        can_go_negative=True,
        min_value=-10,
    ))
    
    # Progression
    vocab.add_field(FieldDefinition(
        key="level",
        label="Level",
        semantic_role=SemanticRole.PROGRESSION,
        field_type=FieldType.NUMBER,
        default_value=1,
        min_value=1,
        max_value=20,
    ))
    
    vocab.add_field(FieldDefinition(
        key="xp",
        label="Experience Points",
        semantic_role=SemanticRole.PROGRESSION,
        field_type=FieldType.NUMBER,
        default_value=0,
        min_value=0,
    ))
    
    return vocab


def create_fate_like_vocabulary(system_name: str = "Fate Core") -> GameVocabulary:
    """
    Create a vocabulary for Fate-like systems.
    
    Demonstrates non-D&D field types (ladders, tracks, tags).
    """
    vocab = GameVocabulary(
        system_name=system_name,
        system_id=system_name.lower().replace(" ", "_"),
        genre="universal",
        dice_notation="4dF",
        resolution_mechanic="4dF + skill vs opposition",
        terminology={
            "damage": "stress",
            "health": "stress track",
            "critical": "boost",
        },
    )
    
    # Ladder labels for Fate
    fate_ladder = {
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
    
    # Approaches (FAE style)
    for key, label in [
        ("careful", "Careful"),
        ("clever", "Clever"),
        ("flashy", "Flashy"),
        ("forceful", "Forceful"),
        ("quick", "Quick"),
        ("sneaky", "Sneaky"),
    ]:
        vocab.add_field(FieldDefinition(
            key=key,
            label=label,
            semantic_role=SemanticRole.CORE_TRAIT,
            field_type=FieldType.LADDER,
            default_value=1,
            min_value=-1,
            max_value=6,
            ladder_labels=fate_ladder,
        ))
    
    # Stress tracks
    vocab.add_field(FieldDefinition(
        key="physical_stress",
        label="Physical Stress",
        semantic_role=SemanticRole.RESOURCE,
        field_type=FieldType.TRACK,
        track_length=3,
    ))
    
    vocab.add_field(FieldDefinition(
        key="mental_stress",
        label="Mental Stress",
        semantic_role=SemanticRole.RESOURCE,
        field_type=FieldType.TRACK,
        track_length=3,
    ))
    
    # Fate points
    vocab.add_field(FieldDefinition(
        key="fate_points",
        label="Fate Points",
        semantic_role=SemanticRole.RESOURCE,
        field_type=FieldType.NUMBER,
        default_value=3,
        min_value=0,
    ))
    
    # Aspects
    vocab.add_field(FieldDefinition(
        key="high_concept",
        label="High Concept",
        semantic_role=SemanticRole.ASPECT,
        field_type=FieldType.TAG,
    ))
    
    vocab.add_field(FieldDefinition(
        key="trouble",
        label="Trouble",
        semantic_role=SemanticRole.ASPECT,
        field_type=FieldType.TAG,
    ))
    
    # Consequences
    for severity in ["mild", "moderate", "severe"]:
        vocab.add_field(FieldDefinition(
            key=f"{severity}_consequence",
            label=f"{severity.title()} Consequence",
            semantic_role=SemanticRole.STATUS,
            field_type=FieldType.TAG,
        ))
    
    return vocab
