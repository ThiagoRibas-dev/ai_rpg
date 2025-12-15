"""
Vocabulary Extractor
====================
Extracts a GameVocabulary from rules text using LLM.
Updated: Fail-fast architecture (raises exceptions).
"""

import logging
from typing import List, Optional, Dict, Any, Callable, Set

from pydantic import BaseModel

from app.llm.llm_connector import LLMConnector
from app.models.message import Message
from app.models.vocabulary import (
    GameVocabulary,
    FieldDefinition,
    FieldType,
    SemanticRole,
)
from app.prompts.templates import (
    SHARED_RULES_SYSTEM_PROMPT,
    VOCABULARY_ANALYSIS_INSTRUCTION,
    VOCABULARY_GROUP_INSTRUCTION,
)

logger = logging.getLogger(__name__)

# --- SCHEMAS ---


class ExtractedField(BaseModel):
    key: str
    label: str
    description: str = ""
    semantic_role: str
    field_type: str
    min_value: Optional[int] = None
    max_value: Optional[int] = None
    default_value: Optional[Any] = None
    track_length: Optional[int] = None
    die_default: Optional[str] = None
    ladder_labels: Optional[Dict[int, str]] = None
    governing_trait: Optional[str] = None
    can_go_negative: bool = False
    formula: Optional[str] = None


class ExtractedFieldList(BaseModel):
    fields: List[ExtractedField]


class ExtractedVocabularyMeta(BaseModel):
    system_name: str
    system_id: str
    genre: str = "fantasy"
    dice_notation: str = "d20"
    resolution_mechanic: str = ""
    terminology: Dict[str, str] = {}


# --- EXTRACTOR ---


class VocabularyExtractor:
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
        # 1. Analysis Phase
        self._update_status("Analyzing game system...")
        analysis_history = [
            Message(role="user", content=VOCABULARY_ANALYSIS_INSTRUCTION)
        ]

        # We allow streaming to fail if the connector doesn't support it,
        # but if it errors out completely, we let it raise.
        try:
            response_stream = self.llm.get_streaming_response(
                system_prompt=system_prompt, chat_history=analysis_history
            )
            # Consume stream to ensure API call completes
            list(response_stream)
        except Exception as e:
            logger.warning(f"Analysis stream warning (non-fatal): {e}")

        # 2. Metadata Extraction
        self._update_status("Extracting system metadata...")
        # No try/except here - Fail Fast
        meta = self.llm.get_structured_response(
            system_prompt=system_prompt,
            chat_history=analysis_history,
            output_schema=ExtractedVocabularyMeta,
            temperature=0.2,
        )

        vocab = GameVocabulary(
            system_name=meta.system_name,
            system_id=meta.system_id,
            genre=meta.genre,
            dice_notation=meta.dice_notation,
            resolution_mechanic=meta.resolution_mechanic,
            terminology=meta.terminology,
        )

        # 3. Iterative Field Extraction
        groups = [
            ("Core Stats", ["core_trait", "resource", "progression"]),
            ("Capabilities", ["capability"]),
            ("State & Gear", ["status", "aspect", "equipment", "connection"]),
        ]

        seen_keys: Set[str] = set()

        for group_name, roles in groups:
            self._update_status(f"Extracting {group_name}...")

            keys_list = ", ".join(sorted(list(seen_keys)))
            if not keys_list:
                keys_list = "(None)"

            instruction = VOCABULARY_GROUP_INSTRUCTION.format(
                group_name=group_name, roles=", ".join(roles), existing_keys=keys_list
            )

            step_history = analysis_history + [
                Message(role="user", content=instruction)
            ]

            # Fail Fast: If extraction fails, stop the whole process
            result = self.llm.get_structured_response(
                system_prompt=system_prompt,
                chat_history=step_history,
                output_schema=ExtractedFieldList,
                temperature=0.2,
            )

            for ef in result.fields:
                if ef.key in seen_keys:
                    continue
                try:
                    field_def = self._convert_field(ef)
                    vocab.add_field(field_def)
                    seen_keys.add(ef.key)
                except Exception as e:
                    logger.warning(f"Skipping invalid field {ef.key}: {e}")

        return vocab

    def _convert_field(self, ef: ExtractedField) -> FieldDefinition:
        try:
            role = SemanticRole(ef.semantic_role.lower().replace(" ", "_"))
        except ValueError:
            role = SemanticRole.CORE_TRAIT

        try:
            ftype = FieldType(ef.field_type.lower().replace(" ", "_"))
        except ValueError:
            ftype = FieldType.NUMBER

        ladder_labels = None
        if ef.ladder_labels:
            ladder_labels = {}
            for k, v in ef.ladder_labels.items():
                try:
                    ladder_labels[int(k)] = str(v)
                except (ValueError, TypeError):
                    pass

        return FieldDefinition(
            key=ef.key,
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


# --- CONVENIENCE ---
def extract_vocabulary_from_text(
    llm: LLMConnector,
    rules_text: str,
    status_callback: Optional[Callable[[str], None]] = None,
) -> GameVocabulary:
    system_prompt = SHARED_RULES_SYSTEM_PROMPT.format(rules_source=rules_text)
    extractor = VocabularyExtractor(llm, status_callback)
    return extractor.extract(system_prompt)
