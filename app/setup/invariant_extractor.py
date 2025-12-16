"""
Invariant Extractor
===================
Two-phase approach:
1. STRUCTURAL invariants derived from vocabulary (no LLM)
2. EDGE CASE invariants from LLM (game-specific only)
"""

import logging
from typing import List, Optional, Callable, Literal

from pydantic import BaseModel, Field

from app.llm.llm_connector import LLMConnector
from app.models.message import Message
from app.models.vocabulary import (
    GameVocabulary,
    FieldType,
    ROLE_TO_CATEGORY,
)
from app.models.ruleset import StateInvariant

logger = logging.getLogger(__name__)


# =============================================================================
# STRUCTURAL INVARIANTS (No LLM - Derived from Vocabulary)
# =============================================================================


def generate_structural_invariants(vocab: GameVocabulary) -> List[StateInvariant]:
    """
    Generate invariants purely from vocabulary structure.
    These are universal patterns that apply to any game.

    Returns:
        List of StateInvariant objects
    """
    invariants = []

    for full_key, field in vocab.fields.items():
        category = ROLE_TO_CATEGORY.get(field.semantic_role, field.semantic_role.value)
        base_path = f"{category}.{field.key}"

        # === POOL: current <= max ===
        if field.field_type == FieldType.POOL:
            invariants.append(
                StateInvariant(
                    name=f"{field.label} bounded by maximum",
                    target_path=f"{base_path}.current",
                    constraint="<=",
                    reference=f"{base_path}.max",
                    on_violation="clamp",
                )
            )

            # Also: current >= 0 (unless can_go_negative)
            if not field.can_go_negative:
                invariants.append(
                    StateInvariant(
                        name=f"{field.label} non-negative",
                        target_path=f"{base_path}.current",
                        constraint=">=",
                        reference="0",
                        on_violation="clamp",
                    )
                )

        # === NUMBER with bounds ===
        if field.field_type == FieldType.NUMBER:
            if field.min_value is not None:
                invariants.append(
                    StateInvariant(
                        name=f"{field.label} minimum",
                        target_path=base_path,
                        constraint=">=",
                        reference=str(field.min_value),
                        on_violation="clamp",
                    )
                )

            if field.max_value is not None:
                invariants.append(
                    StateInvariant(
                        name=f"{field.label} maximum",
                        target_path=base_path,
                        constraint="<=",
                        reference=str(field.max_value),
                        on_violation="clamp",
                    )
                )

        # === TRACK: filled <= length ===
        if field.field_type == FieldType.TRACK and field.track_length:
            invariants.append(
                StateInvariant(
                    name=f"{field.label} track limit",
                    target_path=f"{base_path}.filled",
                    constraint="<=",
                    reference=str(field.track_length),
                    on_violation="clamp",
                )
            )

            invariants.append(
                StateInvariant(
                    name=f"{field.label} track non-negative",
                    target_path=f"{base_path}.filled",
                    constraint=">=",
                    reference="0",
                    on_violation="clamp",
                )
            )

        # === LADDER: value in range ===
        if field.field_type == FieldType.LADDER:
            if field.min_value is not None:
                invariants.append(
                    StateInvariant(
                        name=f"{field.label} ladder minimum",
                        target_path=f"{base_path}.value",
                        constraint=">=",
                        reference=str(field.min_value),
                        on_violation="clamp",
                    )
                )

            if field.max_value is not None:
                invariants.append(
                    StateInvariant(
                        name=f"{field.label} ladder maximum",
                        target_path=f"{base_path}.value",
                        constraint="<=",
                        reference=str(field.max_value),
                        on_violation="clamp",
                    )
                )

    return invariants


# =============================================================================
# EDGE CASE EXTRACTION (LLM - Game-Specific Only)
# =============================================================================


class InvariantTarget(BaseModel):
    """Structured target - components are validated against vocabulary."""

    category: str = Field(
        ..., description="Category like 'attributes', 'resources', 'skills'"
    )
    field_key: str = Field(..., description="The specific field key")
    sub_component: Optional[str] = Field(
        None, description="Sub-path like 'current', 'max', 'value', 'filled'"
    )


class StructuredConstraint(BaseModel):
    """Constraint with explicit operator and reference."""

    operator: Literal[">=", "<=", "==", "!=", "in_range"] = Field(
        ..., description="Comparison operator"
    )
    reference_type: Literal["literal", "field"] = Field(
        ..., description="Whether reference is a literal value or another field path"
    )
    reference_value: str = Field(
        ...,
        description="The literal value (e.g., '0', '-10') or field path (e.g., 'resources.hp.max')",
    )


class EdgeCaseInvariant(BaseModel):
    """LLM-extracted edge case invariant."""

    name: str = Field(..., description="Descriptive name for the constraint")
    target: InvariantTarget
    constraint: StructuredConstraint
    on_violation: Literal["clamp", "flag", "reject"] = "clamp"
    reason: str = Field("", description="Why this constraint exists in the rules")


class EdgeCaseList(BaseModel):
    """Container for edge case invariants."""

    invariants: List[EdgeCaseInvariant] = Field(default_factory=list)


EDGE_CASE_PROMPT = """
The following STANDARD constraints are already handled automatically:
- Pool resources: current <= max, current >= 0
- Bounded numbers: value within min/max
- Tracks: filled boxes within track length

Identify any SPECIAL CONSTRAINTS from the rules that are NOT covered above.

Examples of special constraints:
- A value that CAN go negative (e.g., "HP can go to -10 before death")
- Cross-field dependencies (e.g., "Skill ranks cannot exceed Level + 3")
- Conditional caps (e.g., "Stress triggers breakdown when exceeding Composure")
- Mutually exclusive states

Only list constraints UNIQUE to this system. Do not repeat the standard patterns.

Available categories: {categories}
Available fields per category:
{field_hints}
"""


class InvariantExtractor:
    """
    Two-phase invariant extraction:
    1. Structural (from vocabulary - no LLM)
    2. Edge cases (LLM - game-specific only)
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
        logger.info(f"[InvariantExtractor] {message}")

    def extract(
        self, vocab: GameVocabulary, system_prompt: str
    ) -> List[StateInvariant]:
        """
        Main extraction pipeline.

        Args:
            vocab: Already-extracted vocabulary
            system_prompt: Shared rules context

        Returns:
            Combined list of structural + edge case invariants
        """
        # Phase 1: Structural (no LLM)
        self._update_status("Generating structural invariants...")
        structural = generate_structural_invariants(vocab)
        self._update_status(f"Generated {len(structural)} structural invariants")

        # Phase 2: Edge cases (LLM)
        self._update_status("Extracting edge case invariants...")
        edge_cases = self._extract_edge_cases(vocab, system_prompt)
        self._update_status(f"Extracted {len(edge_cases)} edge case invariants")

        return structural + edge_cases

    def _extract_edge_cases(
        self, vocab: GameVocabulary, system_prompt: str
    ) -> List[StateInvariant]:
        """
        Extract game-specific invariants that aren't structural.
        """
        # Build field hints for the prompt
        categories = set()
        field_hints_parts = []

        for full_key, field in vocab.fields.items():
            category = ROLE_TO_CATEGORY.get(
                field.semantic_role, field.semantic_role.value
            )
            categories.add(category)

            sub_paths = field.get_sub_paths()
            if sub_paths:
                sub_str = ", ".join(f".{s}" for s in sub_paths[:3])
                field_hints_parts.append(f"  - {category}.{field.key} ({sub_str})")
            else:
                field_hints_parts.append(f"  - {category}.{field.key}")

        prompt = EDGE_CASE_PROMPT.format(
            categories=", ".join(sorted(categories)),
            field_hints="\n".join(field_hints_parts),  # Limit for context
        )

        try:
            result = self.llm.get_structured_response(
                system_prompt=system_prompt,
                chat_history=[Message(role="user", content=prompt)],
                output_schema=EdgeCaseList,
                temperature=0.5,
            )

            # Convert and validate
            valid_invariants = []
            for ec in result.invariants:
                invariant = self._build_invariant(ec, vocab)
                if invariant:
                    valid_invariants.append(invariant)

            return valid_invariants

        except Exception as e:
            logger.warning(f"Edge case extraction failed: {e}")
            return []

    def _build_invariant(
        self, ec: EdgeCaseInvariant, vocab: GameVocabulary
    ) -> Optional[StateInvariant]:
        """
        Build StateInvariant from extracted edge case.
        Validates path against vocabulary.
        """
        # Build path from components
        base_path = f"{ec.target.category}.{ec.target.field_key}"

        if ec.target.sub_component:
            full_path = f"{base_path}.{ec.target.sub_component}"
        else:
            full_path = base_path

        # Validate path
        if not vocab.validate_path(full_path):
            logger.warning(f"Invalid path in invariant '{ec.name}': {full_path}")
            return None

        # Build reference
        if ec.constraint.reference_type == "field":
            # Validate reference path too
            if not vocab.validate_path(ec.constraint.reference_value):
                logger.warning(
                    f"Invalid reference path in invariant '{ec.name}': "
                    f"{ec.constraint.reference_value}"
                )
                return None

        return StateInvariant(
            name=ec.name,
            target_path=full_path,
            constraint=ec.constraint.operator,
            reference=ec.constraint.reference_value,
            on_violation=ec.on_violation,
        )


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================


def extract_invariants(
    llm: LLMConnector,
    vocab: GameVocabulary,
    rules_text: str,
    status_callback: Optional[Callable[[str], None]] = None,
) -> List[StateInvariant]:
    """
    Convenience function to extract all invariants.
    """
    from app.prompts.templates import SHARED_RULES_SYSTEM_PROMPT

    system_prompt = SHARED_RULES_SYSTEM_PROMPT.format(rules_source=rules_text)
    extractor = InvariantExtractor(llm, status_callback)
    return extractor.extract(vocab, system_prompt)
