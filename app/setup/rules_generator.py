"""
Rules Generator
===============
Orchestrates the extraction pipeline.
Updated to use new vocabulary and invariant extractors.
"""

import logging
from typing import List, Optional, Callable, Tuple, Dict, Any

from pydantic import BaseModel

from app.llm.llm_connector import LLMConnector
from app.models.message import Message
from app.models.ruleset import Ruleset, EngineConfig, ProcedureDef
from app.models.vocabulary import GameVocabulary
from app.setup.vocabulary_extractor import VocabularyExtractor
from app.setup.invariant_extractor import (
    InvariantExtractor,
)
from app.prompts.templates import (
    SHARED_RULES_SYSTEM_PROMPT,
    EXTRACT_ENGINE_INSTRUCTION,
    EXTRACT_PROCEDURE_INSTRUCTION,
    IDENTIFY_RULE_CATEGORIES_INSTRUCTION,
    EXTRACT_RULE_CATEGORY_INSTRUCTION,
)

logger = logging.getLogger(__name__)


# =============================================================================
# SCHEMAS
# =============================================================================


class RuleEntry(BaseModel):
    name: str
    content: str
    tags: List[str]


class RuleList(BaseModel):
    rules: List[RuleEntry]


class RuleCategoryList(BaseModel):
    categories: List[str]


class EngineMetadata(BaseModel):
    name: str
    genre: str
    dice_notation: str
    roll_mechanic: str
    success_condition: str
    crit_rules: str
    sheet_hints: List[str] = []


# =============================================================================
# MAIN GENERATOR
# =============================================================================


class RulesGenerator:
    """
    Orchestrates the full extraction pipeline:
    1. Vocabulary (role-scoped)
    2. Engine metadata
    3. Invariants (structural + edge cases)
    4. Procedures
    5. Mechanics/Rules
    """

    def __init__(
        self, llm: LLMConnector, status_callback: Optional[Callable[[str], None]] = None
    ):
        self.llm = llm
        self.status_callback = status_callback
        self.total_steps = 5
        self.current_step = 0

    def _update_status(self, message: str):
        if self.status_callback:
            prefix = f"[Step {self.current_step}/{self.total_steps}]"
            self.status_callback(f"{prefix} {message}")
        logger.info(f"[RulesGen] {message}")

    def generate_ruleset(
        self, rules_text: str
    ) -> Tuple[Ruleset, List[Dict[str, Any]], GameVocabulary]:
        """
        Main extraction pipeline.

        Args:
            rules_text: Raw rules text to process

        Returns:
            Tuple of (Ruleset, base_rules list, GameVocabulary)
        """
        # === 0. BUILD SHARED CONTEXT ===
        self.current_step = 0
        self._update_status("Ingesting rules text...")
        system_prompt = SHARED_RULES_SYSTEM_PROMPT.format(rules_source=rules_text)

        # === PHASE 1: VOCABULARY ===
        self.current_step = 1
        self._update_status("Extracting game vocabulary...")

        vocab_extractor = VocabularyExtractor(self.llm, self._create_sub_callback())
        vocabulary = vocab_extractor.extract(system_prompt)

        self._update_status(f"Vocabulary: {len(vocabulary.fields)} fields extracted")

        # === PHASE 2: ENGINE META ===
        self.current_step = 2
        self._update_status("Analyzing core engine...")

        engine_meta = self.llm.get_structured_response(
            system_prompt=system_prompt,
            chat_history=[Message(role="user", content=EXTRACT_ENGINE_INSTRUCTION)],
            output_schema=EngineMetadata,
            temperature=0.5,
        )

        ruleset = Ruleset(
            meta={"name": engine_meta.name, "genre": engine_meta.genre},
            engine=EngineConfig(
                dice_notation=engine_meta.dice_notation,
                roll_mechanic=engine_meta.roll_mechanic,
                success_condition=engine_meta.success_condition,
                crit_rules=engine_meta.crit_rules,
            ),
            sheet_hints=engine_meta.sheet_hints,
        )

        # === PHASE 3: INVARIANTS ===
        self.current_step = 3
        self._update_status("Generating invariants...")

        inv_extractor = InvariantExtractor(self.llm, self._create_sub_callback())
        all_invariants = inv_extractor.extract(vocabulary, system_prompt)

        ruleset.state_invariants = all_invariants
        self._update_status(f"Invariants: {len(all_invariants)} total")

        # === PHASE 4: PROCEDURES ===
        self.current_step = 4
        self._update_status("Extracting procedures...")

        self._extract_procedures(ruleset, system_prompt)

        # === PHASE 5: MECHANICS ===
        self.current_step = 5
        self._update_status("Indexing mechanics...")

        rule_dicts = self._extract_mechanics(system_prompt)

        # Deduplicate
        rule_dicts = self._deduplicate_rules(rule_dicts)

        self._update_status("Rules generation complete!")
        return ruleset, rule_dicts, vocabulary

    def _create_sub_callback(self) -> Optional[Callable[[str], None]]:
        """Create a sub-callback that preserves step context."""
        if not self.status_callback:
            return None

        step = self.current_step
        total = self.total_steps

        def sub_callback(msg: str):
            self.status_callback(f"[Step {step}/{total}] {msg}")

        return sub_callback

    def _extract_procedures(self, ruleset: Ruleset, system_prompt: str):
        """Extract game mode procedures."""
        target_modes = [
            ("combat", ruleset.combat_procedures),
            ("exploration", ruleset.exploration_procedures),
            ("social", ruleset.social_procedures),
            ("downtime", ruleset.downtime_procedures),
        ]

        for mode_name, target_dict in target_modes:
            self._update_status(f"Extracting {mode_name} procedure...")

            try:
                proc_instruction = EXTRACT_PROCEDURE_INSTRUCTION.format(
                    mode_name=mode_name
                )

                proc = self.llm.get_structured_response(
                    system_prompt=system_prompt,
                    chat_history=[Message(role="user", content=proc_instruction)],
                    output_schema=ProcedureDef,
                    temperature=0.5,
                )

                if proc.steps:
                    target_dict[mode_name] = proc

            except Exception as e:
                logger.warning(f"Failed to extract {mode_name} procedure: {e}")
                continue

    def _extract_mechanics(self, system_prompt: str) -> List[Dict[str, Any]]:
        """Extract specific game rules and mechanics."""
        rule_dicts = []

        # Identify categories
        try:
            cats_result = self.llm.get_structured_response(
                system_prompt=system_prompt,
                chat_history=[
                    Message(role="user", content=IDENTIFY_RULE_CATEGORIES_INSTRUCTION)
                ],
                output_schema=RuleCategoryList,
                temperature=0.7,
            )
            categories = cats_result.categories
        except Exception as e:
            logger.warning(f"Failed to identify rule categories: {e}")
            categories = ["core", "combat", "powers", "skills", "social"]

        # Extract per category
        for cat in categories:
            self._update_status(f"Extracting rules: {cat}...")

            try:
                mech_instruction = EXTRACT_RULE_CATEGORY_INSTRUCTION.format(
                    category=cat
                )

                mech_result = self.llm.get_structured_response(
                    system_prompt=system_prompt,
                    chat_history=[Message(role="user", content=mech_instruction)],
                    output_schema=RuleList,
                    temperature=0.3,
                )

                for r in mech_result.rules:
                    rule_dicts.append(
                        {
                            "kind": "rule",
                            "content": f"{r.name}: {r.content}",
                            "tags": r.tags + ["rule", cat.lower().replace(" ", "_")],
                        }
                    )

            except Exception as e:
                logger.warning(f"Failed to extract {cat} rules: {e}")
                continue

        return rule_dicts

    def _deduplicate_rules(self, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove near-duplicate rules."""
        import hashlib
        import re

        seen_hashes = set()
        unique = []

        for rule in rules:
            # Normalize content for comparison
            content = rule.get("content", "")
            normalized = re.sub(r"\s+", " ", content.lower().strip())

            # Hash first 200 chars
            content_hash = hashlib.md5(normalized[:200].encode()).hexdigest()

            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique.append(rule)

        if len(rules) != len(unique):
            logger.info(f"Deduplicated rules: {len(rules)} -> {len(unique)}")

        return unique
