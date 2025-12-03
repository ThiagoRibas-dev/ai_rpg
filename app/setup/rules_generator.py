import logging
from typing import List, Optional, Callable
from pydantic import BaseModel

from app.llm.llm_connector import LLMConnector
from app.models.message import Message
from app.models.ruleset import Ruleset, PhysicsConfig, GameLoopConfig, ProcedureDef, RuleEntry
from app.prompts.templates import (
    TEMPLATE_GENERATION_SYSTEM_PROMPT,
    IDENTIFY_MODES_INSTRUCTION,
    EXTRACT_PROCEDURE_INSTRUCTION,
    GENERATE_MECHANICS_INSTRUCTION
)

logger = logging.getLogger(__name__)

class RulesGenerator:
    def __init__(self, llm: LLMConnector, status_callback: Optional[Callable[[str], None]] = None):
        self.llm = llm
        self.status_callback = status_callback

    def _update_status(self, message: str):
        if self.status_callback:
            self.status_callback(message)
        logger.info(f"[RulesGen] {message}")

    def generate_ruleset(self, rules_text: str) -> Ruleset:
        # 1. System Prompt
        base_prompt = f"{TEMPLATE_GENERATION_SYSTEM_PROMPT}\n\n# RULES REFERENCE\n{rules_text}"
        
        # 2. Extract Metadata & Physics
        self._update_status("Analyzing Core Physics...")
        class QuickMeta(BaseModel):
            name: str
            genre: str
            dice_notation: str
            roll_mechanic: str
            success_condition: str
            crit_rules: str

        meta_res = self.llm.get_structured_response(
            base_prompt,
            [Message(role="user", content="Extract Game Name, Genre, and Core Dice Mechanics.")],
            QuickMeta
        )

        game_name = meta_res.name
        system_prompt = base_prompt.replace("{target_game}", game_name)

        # 3. Extract Procedures (Game Modes)
        self._update_status("Identifying Game Loops...")
        class GameModes(BaseModel):
            names: List[str]

        modes = self.llm.get_structured_response(
            system_prompt,
            [Message(role="user", content=IDENTIFY_MODES_INSTRUCTION)],
            GameModes
        )

        loops = GameLoopConfig()
        # Limit to 6 modes to save time/tokens
        target_modes = modes.names[:6] if modes and modes.names else []
        
        for mode in target_modes:
            self._update_status(f"Extracting Procedure: {mode}...")
            try:
                proc = self.llm.get_structured_response(
                    system_prompt,
                    [Message(role="user", content=EXTRACT_PROCEDURE_INSTRUCTION.format(mode_name=mode))],
                    ProcedureDef
                )
                
                m = mode.lower()
                if "combat" in m or "encounter" in m: 
                    loops.encounter[mode] = proc
                elif "exploration" in m or "travel" in m: 
                    loops.exploration[mode] = proc
                elif "social" in m: 
                    loops.social[mode] = proc
                elif "downtime" in m: 
                    loops.downtime[mode] = proc
                else: 
                    loops.misc[mode] = proc
            except Exception as e:
                logger.warning(f"Failed to extract procedure for {mode}: {e}")

        # 4. Extract Mechanics (RAG Entries)
        self._update_status("Indexing Mechanics...")
        class MechDict(BaseModel):
            items: dict[str, RuleEntry]

        try:
            mech_res = self.llm.get_structured_response(
                system_prompt,
                [Message(role="user", content=GENERATE_MECHANICS_INSTRUCTION)],
                MechDict
            )
            rules_items = mech_res.items
        except Exception as e:
            logger.warning(f"Failed to extract mechanics: {e}")
            rules_items = {}

        # 5. Assemble
        return Ruleset(
            meta={"name": game_name, "genre": meta_res.genre},
            physics=PhysicsConfig(
                dice_notation=meta_res.dice_notation,
                roll_mechanic=meta_res.roll_mechanic,
                success_condition=meta_res.success_condition,
                crit_rules=meta_res.crit_rules,
            ),
            gameplay_procedures=loops,
            rules=rules_items
        )