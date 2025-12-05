import logging
from typing import List, Optional, Callable, Tuple, Dict, Any
from pydantic import BaseModel

from app.llm.llm_connector import LLMConnector
from app.models.message import Message
from app.models.ruleset import Ruleset, EngineConfig, ProcedureDef
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
    def __init__(
        self, llm: LLMConnector, status_callback: Optional[Callable[[str], None]] = None
    ):
        self.llm = llm
        self.status_callback = status_callback

    def _update_status(self, message: str):
        if self.status_callback:
            self.status_callback(message)
        logger.info(f"[RulesGen] {message}")

    def generate_ruleset(self, rules_text: str) -> Tuple[Ruleset, List[Dict[str, Any]]]:
        # 1. System Prompt
        base_prompt = (
            f"{TEMPLATE_GENERATION_SYSTEM_PROMPT}\n\n# RULES REFERENCE\n{rules_text}"
        )

        # 2. Extract Metadata & Engine
        self._update_status("Analyzing Core Engine...")

        class QuickMeta(BaseModel):
            name: str
            genre: str
            dice_notation: str
            roll_mechanic: str
            success_condition: str
            crit_rules: str
            sheet_hints: List[str]

        meta_res = self.llm.get_structured_response(
            base_prompt,
            [
                Message(
                    role="user",
                    content="Extract Game Name, Genre, Core Engine, and Sheet Hints.",
                )
            ],
            QuickMeta,
        )

        game_name = meta_res.name
        system_prompt = base_prompt.replace("{target_game}", game_name)

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

        # 3. Extract Procedures
        self._update_status("Identifying Game Loops...")

        class GameModes(BaseModel):
            names: List[str]

        modes = self.llm.get_structured_response(
            system_prompt,
            [Message(role="user", content=IDENTIFY_MODES_INSTRUCTION)],
            GameModes,
        )

        target_modes = modes.names[:6] if modes and modes.names else []

        for mode in target_modes:
            self._update_status(f"Extracting Procedure: {mode}...")
            try:
                proc = self.llm.get_structured_response(
                    system_prompt,
                    [
                        Message(
                            role="user",
                            content=EXTRACT_PROCEDURE_INSTRUCTION.format(
                                mode_name=mode
                            ),
                        )
                    ],
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

        # 4. Extract Mechanics as List (Memories)
        self._update_status("Indexing Mechanics...")

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
                rule_dicts.append(
                    {
                        "kind": "rule",
                        "content": f"{r.name}: {r.content}",
                        "tags": r.tags + ["rule", "mechanic"],
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to extract mechanics: {e}")

        return ruleset, rule_dicts
