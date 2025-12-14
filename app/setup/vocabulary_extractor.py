"""
Vocabulary Extractor
====================
Extracts a GameVocabulary from rules text using LLM.

This is the first step in the rules generation pipeline. The extracted
vocabulary becomes the single source of truth for all subsequent steps:
- Schema generation
- Invariant extraction
- Tool hints
- Entity validation

The extractor uses a two-phase approach:
1. Analysis: LLM reads rules and reasons about the system
2. Extraction: LLM outputs structured vocabulary data
"""

import logging
from typing import List, Optional, Dict, Any, Callable

from pydantic import BaseModel, Field

from app.llm.llm_connector import LLMConnector
from app.models.message import Message
from app.models.vocabulary import (
    GameVocabulary,
    FieldDefinition,
    FieldType,
    SemanticRole,
)

logger = logging.getLogger(__name__)


# =============================================================================
# EXTRACTION SCHEMAS
# =============================================================================
# These are the Pydantic models the LLM outputs.
# They're simpler than FieldDefinition to make extraction more reliable.

class ExtractedField(BaseModel):
    """
    A field extracted from rules text.
    
    This is a simplified version of FieldDefinition optimized for LLM extraction.
    The VocabularyExtractor converts these to full FieldDefinitions.
    """
    
    key: str = Field(
        ...,
        description="Unique snake_case identifier, e.g., 'strength', 'hp', 'stealth'"
    )
    label: str = Field(
        ...,
        description="Human-readable display name, e.g., 'Strength', 'Hit Points', 'Stealth'"
    )
    description: str = Field(
        "",
        description="Brief description of what this field represents"
    )
    
    # Semantic classification
    semantic_role: str = Field(
        ...,
        description="What this field represents: core_trait, resource, capability, status, aspect, progression, equipment, connection"
    )
    
    # Structural classification
    field_type: str = Field(
        ...,
        description="How data is stored: number, pool, track, die, ladder, tag, text, list"
    )
    
    # Type-specific metadata (all optional, use what applies)
    min_value: Optional[int] = Field(
        None,
        description="Minimum allowed value (for number, pool, ladder)"
    )
    max_value: Optional[int] = Field(
        None,
        description="Maximum allowed value (for number, pool, ladder)"
    )
    default_value: Optional[Any] = Field(
        None,
        description="Default/starting value"
    )
    track_length: Optional[int] = Field(
        None,
        description="Number of boxes for track fields"
    )
    die_default: Optional[str] = Field(
        None,
        description="Default die notation for die fields, e.g., 'd8'"
    )
    ladder_labels: Optional[Dict[int, str]] = Field(
        None,
        description="Value-to-label mapping for ladder fields, e.g., {2: 'Fair', 3: 'Good'}"
    )
    governing_trait: Optional[str] = Field(
        None,
        description="Key of the core_trait that governs this capability"
    )
    can_go_negative: bool = Field(
        False,
        description="Whether value can go below 0"
    )
    formula: Optional[str] = Field(
        None,
        description="Formula for derived values, e.g., '(strength - 10) // 2'"
    )


class ExtractedVocabulary(BaseModel):
    """
    Complete vocabulary extraction result from LLM.
    """
    
    system_name: str = Field(
        ...,
        description="Full name of the game system, e.g., 'Dungeons & Dragons 5th Edition'"
    )
    system_id: str = Field(
        ...,
        description="Short snake_case identifier, e.g., 'dnd_5e'"
    )
    genre: str = Field(
        "fantasy",
        description="Primary genre: fantasy, sci-fi, horror, modern, universal, etc."
    )
    
    # Resolution mechanics
    dice_notation: str = Field(
        "d20",
        description="Primary dice used, e.g., 'd20', '2d6', '4dF', 'd100'"
    )
    resolution_mechanic: str = Field(
        "",
        description="How rolls are resolved, e.g., 'Roll + Modifier vs DC', 'Roll under Stat'"
    )
    
    # The extracted fields
    fields: List[ExtractedField] = Field(
        ...,
        description="All fields extracted from the rules"
    )
    
    # System-specific terminology
    terminology: Dict[str, str] = Field(
        default_factory=dict,
        description="System-specific terms, e.g., {'damage': 'Harm', 'health': 'Stress'}"
    )


# =============================================================================
# EXTRACTION PROMPTS
# =============================================================================

VOCABULARY_ANALYSIS_PROMPT = """
You are an expert TTRPG system analyst. Your task is to analyze a ruleset and identify its mechanical building blocks.

Read the rules carefully and identify:

1. **CORE TRAITS** — Primary character statistics that define capabilities
   - D&D: Ability Scores (Strength, Dexterity, etc.)
   - Fate: Approaches (Careful, Clever, etc.) or Skills
   - PbtA: Stats (Cool, Hard, Hot, Sharp, Weird)
   - Kids on Bikes: Stats as die types (Brains d8, Brawn d4)

2. **RESOURCES** — Values that get depleted and recovered
   - D&D: Hit Points, Spell Slots
   - Fate: Stress (track), Fate Points (number)
   - Call of Cthulhu: HP, Sanity, Luck

3. **CAPABILITIES** — Skills, proficiencies, or special abilities
   - D&D: Skills (Athletics, Stealth), Proficiencies
   - Fate: Stunts
   - PbtA: Moves

4. **STATUS** — Temporary conditions or states
   - D&D: Conditions (Poisoned, Stunned, Prone)
   - Fate: Consequences, Boosts
   - Generic: Wounded, Exhausted, Inspired

5. **ASPECTS** — Narrative truths that affect gameplay
   - Fate: High Concept, Trouble, other Aspects
   - Beliefs, Instincts, Goals

6. **PROGRESSION** — How characters advance
   - D&D: Level, XP
   - Fate: Milestones, Refresh
   - PbtA: Advancements

For each field, determine:
- **Storage Type**: How is the data structured?
  - `number`: Simple integer (Strength: 16, Level: 5)
  - `pool`: Current/Max pair (HP: 24/30)
  - `track`: Checkbox array (Stress: ☐☐☒☒)
  - `die`: Die notation (Brains: d8)
  - `ladder`: Named rating (Careful: Good +3)
  - `tag`: Narrative text (Aspect: "Former Soldier")
  - `text`: Free-form text
  - `list`: Array of items

- **Bounds**: What are the minimum/maximum values?
- **Relationships**: Does this derive from or govern other fields?

Analyze the following rules text and prepare to extract the vocabulary.
"""

VOCABULARY_EXTRACTION_PROMPT = """
Based on your analysis, extract the game vocabulary as structured data.

## GUIDELINES

1. **Keys**: Use snake_case for all keys (e.g., `hit_points`, `strength_modifier`)

2. **Semantic Roles**: Choose from:
   - `core_trait`: Primary stats (STR, DEX, Approaches)
   - `resource`: Depletable values (HP, Stress, Fate Points)
   - `capability`: Skills, abilities, moves
   - `status`: Temporary conditions
   - `aspect`: Narrative truths
   - `progression`: XP, level, advancements
   - `equipment`: Gear, inventory (usually as list)
   - `connection`: Relationships, bonds

3. **Field Types**: Choose from:
   - `number`: Simple integer value
   - `pool`: Has current and max values
   - `track`: Array of checkboxes (for stress, harm clocks)
   - `die`: Stores a die type (d4, d8, d12)
   - `ladder`: Rating with labels (Fate-style)
   - `tag`: Narrative text with optional metadata
   - `text`: Free-form string
   - `list`: Collection of items

4. **Be Thorough**: Extract ALL mechanical elements that would appear on a character sheet

5. **Derived Values**: If a value is calculated from others, set `formula` and mark what it derives from

## EXAMPLES

For D&D:
```json
{
  "key": "strength",
  "label": "Strength",
  "semantic_role": "core_trait",
  "field_type": "number",
  "min_value": 1,
  "max_value": 30,
  "default_value": 10
}
```

For Fate:
```json
{
  "key": "careful",
  "label": "Careful",
  "semantic_role": "core_trait",
  "field_type": "ladder",
  "min_value": -1,
  "max_value": 6,
  "ladder_labels": {"-1": "Terrible", "0": "Mediocre", "1": "Average", "2": "Fair", "3": "Good"}
}
```

For Kids on Bikes:
```json
{
  "key": "brains",
  "label": "Brains",
  "semantic_role": "core_trait",
  "field_type": "die",
  "die_default": "d8"
}
```

Now extract the complete vocabulary from the rules.
"""


# =============================================================================
# VOCABULARY EXTRACTOR
# =============================================================================

class VocabularyExtractor:
    """
    Extracts a GameVocabulary from rules text using LLM.
    
    Uses a two-phase approach:
    1. Analysis phase: LLM reads and reasons about the rules
    2. Extraction phase: LLM outputs structured vocabulary
    
    This separation improves extraction quality by letting the LLM
    "think" before producing structured output.
    """
    
    def __init__(
        self,
        llm: LLMConnector,
        status_callback: Optional[Callable[[str], None]] = None,
    ):
        self.llm = llm
        self.status_callback = status_callback
    
    def _update_status(self, message: str):
        """Update status for UI feedback."""
        if self.status_callback:
            self.status_callback(message)
        logger.info(f"[VocabExtractor] {message}")
    
    def extract(self, rules_text: str) -> GameVocabulary:
        """
        Extract vocabulary from rules text.
        
        Args:
            rules_text: The game rules/SRD text to analyze
            
        Returns:
            A fully populated GameVocabulary
        """
        if not rules_text or not rules_text.strip():
            logger.warning("Empty rules text provided, returning minimal vocabulary")
            return self._create_minimal_vocabulary()
        
        # Truncate if too long (preserve beginning which usually has core rules)
        max_length = 12000
        if len(rules_text) > max_length:
            rules_text = rules_text[:max_length] + "\n\n[... truncated for length ...]"
            logger.info(f"Truncated rules text to {max_length} characters")
        
        # Phase 1: Analysis
        self._update_status("Analyzing game system...")
        analysis = self._analyze_rules(rules_text)
        
        # Phase 2: Extraction
        self._update_status("Extracting vocabulary...")
        extracted = self._extract_vocabulary(rules_text, analysis)
        
        # Phase 3: Conversion
        self._update_status("Building vocabulary model...")
        vocabulary = self._convert_to_vocabulary(extracted)
        
        self._update_status(
            f"Extracted {len(vocabulary.fields)} fields for {vocabulary.system_name}"
        )
        
        return vocabulary
    
    def _analyze_rules(self, rules_text: str) -> str:
        """
        Phase 1: Have the LLM analyze and reason about the rules.
        
        Returns the LLM's analysis as text.
        """
        try:
            response_stream = self.llm.get_streaming_response(
                system_prompt=VOCABULARY_ANALYSIS_PROMPT,
                chat_history=[
                    Message(role="user", content=f"# RULES TEXT\n\n{rules_text}")
                ],
            )
            
            analysis = "".join(response_stream)
            logger.debug(f"Analysis complete: {len(analysis)} characters")
            return analysis
            
        except Exception as e:
            logger.error(f"Analysis phase failed: {e}")
            return "Analysis failed. Proceeding with direct extraction."
    
    def _extract_vocabulary(self, rules_text: str, analysis: str) -> ExtractedVocabulary:
        """
        Phase 2: Extract structured vocabulary based on analysis.
        """
        try:
            extracted = self.llm.get_structured_response(
                system_prompt=VOCABULARY_EXTRACTION_PROMPT,
                chat_history=[
                    Message(role="user", content=f"# RULES TEXT\n\n{rules_text}"),
                    Message(role="assistant", content=analysis),
                    Message(role="user", content="Now extract the vocabulary as JSON."),
                ],
                output_schema=ExtractedVocabulary,
                temperature=0.3,  # Lower temperature for more consistent extraction
            )
            
            logger.info(
                f"Extracted: {extracted.system_name} with {len(extracted.fields)} fields"
            )
            return extracted
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}", exc_info=True)
            # Return minimal extraction on failure
            return ExtractedVocabulary(
                system_name="Unknown System",
                system_id="unknown",
                genre="fantasy",
                fields=[],
            )
    
    def _convert_to_vocabulary(self, extracted: ExtractedVocabulary) -> GameVocabulary:
        """
        Convert ExtractedVocabulary to full GameVocabulary.
        
        This adds validation, normalization, and any missing defaults.
        """
        vocab = GameVocabulary(
            system_name=extracted.system_name,
            system_id=extracted.system_id or self._to_snake_case(extracted.system_name),
            genre=extracted.genre,
            dice_notation=extracted.dice_notation,
            resolution_mechanic=extracted.resolution_mechanic,
            terminology=extracted.terminology,
        )
        
        # Convert each extracted field
        for ef in extracted.fields:
            try:
                field = self._convert_field(ef)
                vocab.add_field(field)
            except Exception as e:
                logger.warning(f"Failed to convert field '{ef.key}': {e}")
                continue
        
        # Ensure minimum viable vocabulary
        if not vocab.fields:
            logger.warning("No fields extracted, adding minimal defaults")
            self._add_minimal_fields(vocab)
        
        return vocab
    
    def _convert_field(self, ef: ExtractedField) -> FieldDefinition:
        """
        Convert an ExtractedField to a FieldDefinition.
        
        Handles normalization and validation.
        """
        # Normalize semantic role
        try:
            role = SemanticRole(ef.semantic_role.lower().replace(" ", "_"))
        except ValueError:
            logger.warning(f"Unknown semantic role '{ef.semantic_role}', defaulting to core_trait")
            role = SemanticRole.CORE_TRAIT
        
        # Normalize field type
        try:
            ftype = FieldType(ef.field_type.lower().replace(" ", "_"))
        except ValueError:
            logger.warning(f"Unknown field type '{ef.field_type}', defaulting to number")
            ftype = FieldType.NUMBER
        
        # Normalize key
        key = self._to_snake_case(ef.key)
        
        # Convert ladder_labels keys to integers if needed
        ladder_labels = None
        if ef.ladder_labels:
            ladder_labels = {}
            for k, v in ef.ladder_labels.items():
                try:
                    ladder_labels[int(k)] = str(v)
                except (ValueError, TypeError):
                    pass
        
        return FieldDefinition(
            key=key,
            label=ef.label,
            description=ef.description,
            semantic_role=role,
            field_type=ftype,
            min_value=ef.min_value,
            max_value=ef.max_value,
            default_value=ef.default_value,
            track_length=ef.track_length,
            die_default=ef.die_default,
            ladder_labels=ladder_labels,
            governing_trait=ef.governing_trait,
            can_go_negative=ef.can_go_negative,
            formula=ef.formula,
            is_derived=bool(ef.formula),
        )
    
    def _to_snake_case(self, text: str) -> str:
        """Convert text to snake_case."""
        import re
        # Replace spaces and hyphens with underscores
        text = re.sub(r'[\s\-]+', '_', text)
        # Insert underscore before uppercase letters
        text = re.sub(r'([a-z])([A-Z])', r'\1_\2', text)
        # Remove non-alphanumeric except underscores
        text = re.sub(r'[^a-zA-Z0-9_]', '', text)
        # Lowercase and collapse multiple underscores
        text = re.sub(r'_+', '_', text.lower())
        # Strip leading/trailing underscores
        return text.strip('_')
    
    def _create_minimal_vocabulary(self) -> GameVocabulary:
        """Create a minimal vocabulary when extraction fails."""
        vocab = GameVocabulary(
            system_name="Generic RPG",
            system_id="generic_rpg",
            genre="fantasy",
        )
        self._add_minimal_fields(vocab)
        return vocab
    
    def _add_minimal_fields(self, vocab: GameVocabulary):
        """Add minimal required fields to a vocabulary."""
        # At least one core trait
        vocab.add_field(FieldDefinition(
            key="ability",
            label="Ability",
            semantic_role=SemanticRole.CORE_TRAIT,
            field_type=FieldType.NUMBER,
            default_value=10,
            min_value=1,
        ))
        
        # At least one resource
        vocab.add_field(FieldDefinition(
            key="health",
            label="Health",
            semantic_role=SemanticRole.RESOURCE,
            field_type=FieldType.POOL,
            min_value=0,
        ))
        
        # Progression
        vocab.add_field(FieldDefinition(
            key="level",
            label="Level",
            semantic_role=SemanticRole.PROGRESSION,
            field_type=FieldType.NUMBER,
            default_value=1,
            min_value=1,
        ))


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def extract_vocabulary_from_text(
    llm: LLMConnector,
    rules_text: str,
    status_callback: Optional[Callable[[str], None]] = None,
) -> GameVocabulary:
    """
    Convenience function to extract vocabulary from rules text.
    
    Args:
        llm: The LLM connector to use
        rules_text: The game rules text
        status_callback: Optional callback for status updates
        
    Returns:
        Extracted GameVocabulary
    """
    extractor = VocabularyExtractor(llm, status_callback)
    return extractor.extract(rules_text)
