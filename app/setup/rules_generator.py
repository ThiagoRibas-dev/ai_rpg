"""
Rules Generator
===============
Orchestrates the extraction pipeline using the Forked Context Strategy.
Updated: Step numbering and Fail-Fast error handling.
"""

import logging
from typing import List, Optional, Callable, Tuple, Dict, Any

from pydantic import BaseModel

from app.llm.llm_connector import LLMConnector
from app.models.message import Message
from app.models.ruleset import Ruleset, EngineConfig, ProcedureDef
from app.models.vocabulary import GameVocabulary
from app.setup.vocabulary_extractor import VocabularyExtractor
from app.setup.invariant_extractor import InvariantExtractor
from app.prompts.templates import (
    SHARED_RULES_SYSTEM_PROMPT,
    EXTRACT_ENGINE_INSTRUCTION,
    IDENTIFY_MODES_INSTRUCTION,
    EXTRACT_PROCEDURE_INSTRUCTION,
    IDENTIFY_RULE_CATEGORIES_INSTRUCTION,
    EXTRACT_RULE_CATEGORY_INSTRUCTION,
)

logger = logging.getLogger(__name__)


class RuleEntry(BaseModel):
    name: str
    content: str
    tags: List[str]


class RulesGenerator:
    def __init__(
        self, llm: LLMConnector, status_callback: Optional[Callable[[str], None]] = None
    ):
        self.llm = llm
        self.status_callback = status_callback
        self.total_steps = 5  # Vocab, Engine, Invariants, Procedures, Mechanics
        self.current_step = 0

    def _update_status(self, message: str):
        if self.status_callback:
            # Format: [Step X/Y] Message
            prefix = f"[Step {self.current_step}/{self.total_steps}]"
            self.status_callback(f"{prefix} {message}")
        logger.info(f"[RulesGen] {message}")

    def generate_ruleset(
        self, rules_text: str
    ) -> Tuple[Ruleset, List[Dict[str, Any]], GameVocabulary]:
        # === 0. BUILD SHARED BASE CONTEXT ===
        self.current_step = 0
        self._update_status("Ingesting rules text...")

        system_prompt = SHARED_RULES_SYSTEM_PROMPT.format(rules_source=rules_text)

        # === PHASE 1: VOCABULARY ===
        self.current_step = 1
        self._update_status("Extracting game vocabulary...")

        # Will raise exception if fails
        vocab_extractor = VocabularyExtractor(self.llm, self.status_callback)
        vocabulary = vocab_extractor.extract(system_prompt)

        self._update_status(f"Vocabulary: {len(vocabulary.fields)} fields found.")

        # === PHASE 2: ENGINE META ===
        self.current_step = 2
        self._update_status("Analyzing core engine...")

        class QuickMeta(BaseModel):
            name: str
            genre: str
            dice_notation: str
            roll_mechanic: str
            success_condition: str
            crit_rules: str
            sheet_hints: List[str]

        engine_history = [Message(role="user", content=EXTRACT_ENGINE_INSTRUCTION)]

        # Fail Fast
        meta_res = self.llm.get_structured_response(
            system_prompt=system_prompt,
            chat_history=engine_history,
            output_schema=QuickMeta,
        )

        ruleset = Ruleset(
            meta={"name": meta_res.name, "genre": meta_res.genre},
            engine=EngineConfig(
                dice_notation=meta_res.dice_notation,
                roll_mechanic=meta_res.roll_mechanic,
                success_condition=meta_res.success_condition,
                crit_rules=meta_res.crit_rules,
            ),
            sheet_hints=meta_res.sheet_hints,
        )

        # === PHASE 3: INVARIANTS ===
        self.current_step = 3
        self._update_status("Extracting state invariants...")

        # Will raise exception if fails
        inv_extractor = InvariantExtractor(self.llm, vocabulary, self.status_callback)
        invariants = inv_extractor.extract(system_prompt)
        ruleset.state_invariants = invariants

        # === PHASE 4: PROCEDURES ===
        self.current_step = 4
        self._update_status("Identifying game loops...")

        class GameModes(BaseModel):
            names: List[str]

        mode_history = [Message(role="user", content=IDENTIFY_MODES_INSTRUCTION)]

        # Fail Fast
        modes = self.llm.get_structured_response(
            system_prompt=system_prompt,
            chat_history=mode_history,
            output_schema=GameModes,
        )
        target_modes = modes.names[:6] if modes and modes.names else []

        for mode in target_modes:
            self._update_status(f"Extracting procedure: {mode}...")
            proc_instruction = EXTRACT_PROCEDURE_INSTRUCTION.format(mode_name=mode)
            proc_history = [Message(role="user", content=proc_instruction)]

            # Fail Fast on individual procedures?
            # Strict mode: Yes. If API fails, we stop.
            proc = self.llm.get_structured_response(
                system_prompt=system_prompt,
                chat_history=proc_history,
                output_schema=ProcedureDef,
            )
            m = mode.lower()
            if "combat" in m or "encounter" in m:
                ruleset.combat_procedures[mode] = proc
            elif "exploration" in m or "travel" in m:
                ruleset.exploration_procedures[mode] = proc
            elif "social" in m:
                ruleset.social_procedures[mode] = proc
            elif "downtime" in m:
                ruleset.downtime_procedures[mode] = proc
            else:
                logger.warning(f"Uncategorized mode procedure: {mode}")
                ruleset.other_procedures[mode] = proc

        # === PHASE 5: MECHANICS ===
        self.current_step = 5
        self._update_status("Indexing mechanics...")

        class MechList(BaseModel):
            rules: List[RuleEntry]

        class RuleCats(BaseModel):
            categories: List[str]

        rule_dicts = []

        # 5.1 Identify Categories
        cat_history = [
            Message(role="user", content=IDENTIFY_RULE_CATEGORIES_INSTRUCTION)
        ]

        # Fail Fast
        cats_res = self.llm.get_structured_response(
            system_prompt=system_prompt,
            chat_history=cat_history,
            output_schema=RuleCats,
        )
        target_cats = cats_res.categories[:8]

        # 5.2 Extract per Category
        for cat in target_cats:
            self._update_status(f"Extracting rules: {cat}...")
            mech_instruction = EXTRACT_RULE_CATEGORY_INSTRUCTION.format(category=cat)
            mech_history = [Message(role="user", content=mech_instruction)]

            # Fail Fast
            mech_res = self.llm.get_structured_response(
                system_prompt=system_prompt,
                chat_history=mech_history,
                output_schema=MechList,
            )
            for r in mech_res.rules:
                rule_dicts.append(
                    {
                        "kind": "rule",
                        "content": f"{r.name}: {r.content}",
                        "tags": r.tags + ["rule", cat.lower()],
                    }
                )

        self._update_status("Rules generation complete!")

        return ruleset, rule_dicts, vocabulary
