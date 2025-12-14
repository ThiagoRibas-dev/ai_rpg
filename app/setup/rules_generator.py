"""
Rules Generator
===============
Extracts game rules, vocabulary, and invariants from rules text.

The vocabulary is extracted FIRST and becomes the source of truth for
all subsequent extractions (invariants, procedures, etc.).

Pipeline:
1. Extract Vocabulary (fields, types, roles)
2. Extract Engine Config (dice, resolution)
3. Extract Invariants (using vocabulary paths)
4. Extract Procedures (combat, exploration, etc.)
5. Extract Mechanics (as memories)
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
    TEMPLATE_GENERATION_SYSTEM_PROMPT,
    IDENTIFY_MODES_INSTRUCTION,
    EXTRACT_PROCEDURE_INSTRUCTION,
    GENERATE_MECHANICS_INSTRUCTION,
)

logger = logging.getLogger(__name__)


class RuleEntry(BaseModel):
    name: str
    content: str
    tags: List[str]


class RulesGenerator:
    """
    Extracts a complete Ruleset from rules text.
    
    The extraction is vocabulary-first: we extract the game's vocabulary
    before anything else, then use it to guide subsequent extractions.
    """
    
    def __init__(
        self, 
        llm: LLMConnector, 
        status_callback: Optional[Callable[[str], None]] = None
    ):
        self.llm = llm
        self.status_callback = status_callback

    def _update_status(self, message: str):
        if self.status_callback:
            self.status_callback(message)
        logger.info(f"[RulesGen] {message}")

    def generate_ruleset(
        self, 
        rules_text: str
    ) -> Tuple[Ruleset, List[Dict[str, Any]], GameVocabulary]:
        """
        Generate a complete ruleset from rules text.
        
        Returns:
            Tuple of (Ruleset, base_rules list, GameVocabulary)
        """
        # === PHASE 1: VOCABULARY EXTRACTION ===
        self._update_status("Extracting game vocabulary...")
        
        vocab_extractor = VocabularyExtractor(self.llm, self.status_callback)
        vocabulary = vocab_extractor.extract(rules_text)
        
        self._update_status(
            f"Vocabulary: {len(vocabulary.fields)} fields, "
            f"{len(vocabulary.valid_paths)} paths"
        )
        
        # === PHASE 2: ENGINE EXTRACTION ===
        self._update_status("Analyzing core engine...")
        
        base_prompt = (
            f"{TEMPLATE_GENERATION_SYSTEM_PROMPT}\n\n# RULES REFERENCE\n{rules_text[:8000]}"
        )

        class QuickMeta(BaseModel):
            name: str
            genre: str
            dice_notation: str
            roll_mechanic: str
            success_condition: str
            crit_rules: str
            sheet_hints: List[str]

        try:
            meta_res = self.llm.get_structured_response(
                base_prompt,
                [Message(role="user", content="Extract Game Name, Genre, Core Engine, and Sheet Hints.")],
                QuickMeta,
            )
            
            game_name = meta_res.name
            
            ruleset = Ruleset(
                meta={"name": game_name, "genre": meta_res.genre},
                engine=EngineConfig(
                    dice_notation=meta_res.dice_notation,
                    roll_mechanic=meta_res.roll_mechanic,
                    success_condition=meta_res.success_condition,
                    crit_rules=meta_res.crit_rules,
                ),
                sheet_hints=meta_res.sheet_hints,
            )
        except Exception as e:
            logger.warning(f"Engine extraction failed: {e}")
            ruleset = Ruleset(
                meta={"name": vocabulary.system_name, "genre": vocabulary.genre},
                engine=EngineConfig(
                    dice_notation=vocabulary.dice_notation,
                    roll_mechanic=vocabulary.resolution_mechanic or "Roll + Modifier",
                    success_condition="Meet or exceed target",
                    crit_rules="Natural maximum is critical",
                ),
            )
            game_name = vocabulary.system_name

        system_prompt = base_prompt.replace("{target_game}", game_name)

        # === PHASE 3: INVARIANT EXTRACTION ===
        self._update_status("Extracting state invariants...")
        
        inv_extractor = InvariantExtractor(self.llm, vocabulary, self.status_callback)
        invariants = inv_extractor.extract(rules_text)
        ruleset.state_invariants = invariants
        
        self._update_status(f"Extracted {len(invariants)} invariants")

        # === PHASE 4: PROCEDURE EXTRACTION ===
        self._update_status("Identifying game loops...")

        class GameModes(BaseModel):
            names: List[str]

        try:
            modes = self.llm.get_structured_response(
                system_prompt,
                [Message(role="user", content=IDENTIFY_MODES_INSTRUCTION)],
                GameModes,
            )
            target_modes = modes.names[:6] if modes and modes.names else []
        except Exception:
            target_modes = ["Combat", "Exploration"]

        for mode in target_modes:
            self._update_status(f"Extracting procedure: {mode}...")
            try:
                proc = self.llm.get_structured_response(
                    system_prompt,
                    [Message(role="user", content=EXTRACT_PROCEDURE_INSTRUCTION.format(mode_name=mode))],
                    ProcedureDef,
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
            except Exception as e:
                logger.warning(f"Failed to extract procedure {mode}: {e}")

        # === PHASE 5: MECHANICS EXTRACTION ===
        self._update_status("Indexing mechanics...")

        class MechList(BaseModel):
            rules: List[RuleEntry]

        rule_dicts = []
        try:
            mech_res = self.llm.get_structured_response(
                system_prompt,
                [Message(role="user", content=GENERATE_MECHANICS_INSTRUCTION)],
                MechList,
            )
            for r in mech_res.rules:
                rule_dicts.append({
                    "kind": "rule",
                    "content": f"{r.name}: {r.content}",
                    "tags": r.tags + ["rule", "mechanic"],
                })
        except Exception as e:
            logger.warning(f"Failed to extract mechanics: {e}")

        self._update_status("Rules generation complete!")
        
        return ruleset, rule_dicts, vocabulary
