"""
Vocabulary Extractor
====================
Role-scoped extraction with forced semantic categories.
LLM provides field details, Python builds structure.
"""

import logging
import re
from typing import List, Optional, Callable, Set, Dict

from pydantic import BaseModel, Field

from app.llm.llm_connector import LLMConnector
from app.models.message import Message
from app.models.vocabulary import (
    GameVocabulary,
    FieldDefinition,
    FieldType,
    SemanticRole,
)
from builtins import ValueError

logger = logging.getLogger(__name__)


# =============================================================================
# EXTRACTION SCHEMAS (Minimal - LLM provides only what it must)
# =============================================================================


class ExtractedField(BaseModel):
    """Simplified field for LLM extraction."""

    key: str = Field(..., description="snake_case identifier")
    label: str = Field(..., description="Human-readable name")
    description: str = Field("", description="Brief explanation")
    field_type: FieldType = Field(..., description="Storage type")

    # Optional bounds - LLM provides if known
    min_value: Optional[int] = None
    max_value: Optional[int] = None
    default_value: Optional[int] = None

    # For tracks
    track_length: Optional[int] = None

    # For dice
    die_default: Optional[str] = None

    # For ladders
    # Note: Typed as dict to accept loose LLM JSON, sanitized later.
    ladder_labels: Optional[dict] = None

    # Scope hint
    applies_to: str = Field("pc", description="pc, npc, creature, or all")


class ExtractedFieldList(BaseModel):
    """Container for extracted fields."""

    fields: List[ExtractedField] = Field(default_factory=list)


class SystemMetadata(BaseModel):
    """Basic system info."""

    system_name: str
    system_id: str = ""
    genre: str = "fantasy"
    dice_notation: str = "d20"
    resolution_mechanic: str = ""


# =============================================================================
# ROLE-SPECIFIC PROMPTS (Universal - No Game Examples)
# =============================================================================

ROLE_EXTRACTION_PROMPTS = {
    SemanticRole.CORE_TRAIT: """
Extract the CORE INNATE STATS/ATTRIBUTES for this game system ({game_system}) as individual records in a machine-readable format.

These are:
- Fundamental numbers/ratings that define the character
- Change through character advancement
- Used as base for rolls, derived values, etc

List EACH stat individually (not as a group).
For each, specify the storage type (number, die, ladder, etc.) and typical range.
""",
    SemanticRole.RESOURCE: """
Extract the basic/base DEPLETABLE RESOURCES for this game system ({game_system}) as individual records in a machine-readable format.

These are:
- Pools or tracks that fluctuate during play
- Spent during actions, recovered through rest/abilities
- Examples: health pools, mana, stress, ammunition

List EACH individual base resource that all characters have instead of specific resources gained through advancement.
For pools, note typical current/max range.
For tracks, note how many boxes/levels.
""",
    SemanticRole.CAPABILITY: """
Extract the basic/base SKILLS or TRAINED CAPABILITIES for this game system ({game_system}) as individual records in a machine-readable format.

These are:
- Learned/practiced abilities
- Improve through use or character advancement
- Used or referenced for specific actions

List EACH individual base skill/capability that any character has access to as an individual entry.
Note the rating type (number, die, dots, etc.) and typical range.
""",
    SemanticRole.STATUS: """
Extract the basic TEMPORARY CONDITIONS for this game system ({game_system}) as individual records in a machine-readable format.

These are:
- States that come and go during play
- Applied by effects, removed by time/actions
- Modify other stats or impose penalties

List EACH condition individually.
Note if it's binary (on/off) or has severity levels.
""",
    SemanticRole.ASPECT: """
Extract the basic mechanical NARRATIVE ELEMENTS for this game system ({game_system}) as individual records in a machine-readable format.

These are:
- Story/personality elements that get mechanically invoked
- May be compelled or invoked for bonuses
- Examples: aspects, beliefs, instincts, drives

List EACH type individually.
Note how they're used mechanically.
""",
    SemanticRole.PROGRESSION: """
Extract the basic/base ADVANCEMENT/PROGRESSION tracking values for this game system ({game_system}) as individual records in a machine-readable format.

These are:
- Experience points, levels, tiers
- Advancement currencies or milestones
- Values that track character growth

List EACH progression element individually.
""",
    SemanticRole.EQUIPMENT: """
Extract the basic INVENTORY/EQUIPMENT categories/slots for this game system ({game_system}) as individual records in a machine-readable format.

These are:
- Categories of physical possessions
- May have encumbrance or slot limits
- Weapons, armor, gear, currency

List the slots where equipment/items/possessions go, instead of individual specific items.
Note any special tracking (slots, weight, etc.).
""",
    SemanticRole.CONNECTION: """
Extract the mechanical RELATIONSHIP/CONNECTION that are tracked for this game system ({game_system}) as individual records in a machine-readable format.

These are:
- Links to NPCs, factions, organizations
- May have ratings (trust, influence, etc.)
- Tracked relationships that matter mechanically

List EACH connection type individually.
""",
}

METADATA_EXTRACTION_PROMPT = """
Extract basic system metadata:
1. System name
2. A snake_case identifier
3. Genre (fantasy, sci-fi, horror, etc.)
4. Primary dice notation (d20, 2d6, d100, etc.)
5. Core resolution mechanic (how actions are resolved)
"""


# =============================================================================
# AGGREGATE DETECTION (Heuristic - No Game-Specific Knowledge)
# =============================================================================


def detect_aggregate_field(field: ExtractedField) -> bool:
    """
    Detect if a field appears to be an umbrella that should be expanded.
    Uses heuristics, not game-specific patterns.
    """
    key_lower = field.key.lower()
    desc_lower = field.description.lower()

    signals = [
        # Plural key with singular type
        key_lower.endswith("s") and field.field_type == FieldType.NUMBER,
        key_lower.endswith("es") and field.field_type == FieldType.NUMBER,
        # Description signals aggregation
        "each" in desc_lower,
        "all " in desc_lower,
        "the six" in desc_lower,
        "the three" in desc_lower,
        re.search(r"(\d+)\s+(core|primary|main|basic)", desc_lower) is not None,
        # Common aggregate patterns
        key_lower in ("stats", "attributes", "abilities", "scores"),
        "_scores" in key_lower,
        "_stats" in key_lower,
    ]

    return any(signals)


# =============================================================================
# MAIN EXTRACTOR
# =============================================================================


class VocabularyExtractor:
    """
    Extracts game vocabulary using role-scoped prompts.
    Category assignment is FORCED by extraction phase, not LLM choice.
    """

    def __init__(
        self,
        llm: LLMConnector,
        status_callback: Optional[Callable[[str], None]] = None,
    ):
        self.llm = llm
        self.status_callback = status_callback

    def _update_status(self, message: str):
        if self.status_callback:
            self.status_callback(message)
        logger.info(f"[VocabExtractor] {message}")

    def extract(self, system_prompt: str) -> GameVocabulary:
        """
        Main extraction pipeline.

        Args:
            system_prompt: The shared rules context (from SHARED_RULES_SYSTEM_PROMPT)

        Returns:
            Populated GameVocabulary
        """
        # 1. Extract Metadata
        self._update_status("Extracting system metadata...")
        metadata = self._extract_metadata(system_prompt)

        vocab = GameVocabulary(
            system_name=metadata.system_name,
            system_id=metadata.system_id
            or metadata.system_name.lower().replace(" ", "_"),
            genre=metadata.genre,
            dice_notation=metadata.dice_notation,
            resolution_mechanic=metadata.resolution_mechanic,
        )

        # 2. Extract Fields Per Role (Role is FORCED)
        seen_keys: Set[str] = set()

        for role in SemanticRole:
            prompt = ROLE_EXTRACTION_PROMPTS.get(role)
            if not prompt:
                raise ValueError(f"No extraction prompt defined for role: {role}")

            prompt = prompt.format(game_system=metadata.system_name)

            self._update_status(f"Extracting {role.value}...")

            result = self.llm.get_structured_response(
                system_prompt=system_prompt,
                chat_history=[Message(role="user", content=prompt)],
                output_schema=ExtractedFieldList,
                temperature=0.5,
            )

            for ef in result.fields:
                # Skip duplicates
                if ef.key in seen_keys:
                    logger.warning(f"Duplicate field key detected: {ef.key}, skipping.")
                    continue
                seen_keys.add(ef.key)

                # Build full definition with FORCED role
                field_def = self._build_field_definition(ef, role)
                vocab.add_field(field_def)

        self._update_status(f"Extraction complete: {len(vocab.fields)} fields")
        return vocab

    def _extract_metadata(self, system_prompt: str) -> SystemMetadata:
        """Extract basic system information."""
        try:
            return self.llm.get_structured_response(
                system_prompt=system_prompt,
                chat_history=[Message(role="user", content=METADATA_EXTRACTION_PROMPT)],
                output_schema=SystemMetadata,
                temperature=0.5,
            )
        except Exception as e:
            logger.warning(f"Metadata extraction failed: {e}")
            return SystemMetadata(
                system_name="Unknown System",
                system_id="unknown",
                genre="fantasy",
            )

    def _build_field_definition(
        self, extracted: ExtractedField, role: SemanticRole
    ) -> FieldDefinition:
        """
        Convert extracted field to full definition.
        Role is FORCED by the extraction phase.
        Sanitizes loose types (like ladder_labels) into strict types.
        """

        # Sanitize ladder labels (LLM might return categorical string keys)
        sanitized_ladder = self._sanitize_ladder_labels(extracted.ladder_labels)

        return FieldDefinition(
            key=extracted.key,
            label=extracted.label,
            description=extracted.description,
            semantic_role=role,
            field_type=extracted.field_type,
            min_value=extracted.min_value,
            max_value=extracted.max_value,
            default_value=extracted.default_value,
            track_length=extracted.track_length,
            die_default=extracted.die_default,
            ladder_labels=sanitized_ladder,
            can_go_negative=extracted.min_value is not None and extracted.min_value < 0,
        )

    def _sanitize_ladder_labels(
        self, labels: Optional[dict]
    ) -> Optional[Dict[int, str]]:
        """
        Ensures ladder_labels is strictly Dict[int, str].
        If LLM returns string keys (hallucination), auto-assigns integer indices.
        """
        if not labels:
            return None

        sanitized = {}

        try:
            # Pass 1: Attempt to treat keys as integers (e.g. "1": "Poor")
            all_keys_are_integers = True
            temp_map = {}

            for k, v in labels.items():
                try:
                    int_key = int(k)
                    temp_map[int_key] = str(v)
                except (ValueError, TypeError):
                    all_keys_are_integers = False
                    break

            if all_keys_are_integers:
                return temp_map

            # Pass 2: Fallback for hallucinated categories (e.g. "Magic": "Spells")
            # We map them to an indexed list: 1 -> "Magic: Spells"
            # This preserves the data without breaking the Schema.
            logger.warning(
                "LLM returned non-integer keys for ladder_labels. Sanitizing to index."
            )

            for i, (k, v) in enumerate(labels.items(), start=1):
                # Combine original key and value if they look distinct
                if str(k).lower() not in str(v).lower():
                    sanitized[i] = f"{k}: {v}"
                else:
                    sanitized[i] = str(v)

            return sanitized

        except Exception as e:
            logger.warning(f"Failed to sanitize ladder_labels: {e}")
            return None
