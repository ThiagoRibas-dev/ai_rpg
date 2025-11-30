import logging
from typing import List, Callable, Optional, Tuple
from pydantic import BaseModel

from app.llm.llm_connector import LLMConnector
from app.models.message import Message
from app.models.ruleset import (
    Ruleset,
    PhysicsConfig,
    GameLoopConfig,
    ProcedureDef,
    RuleEntry,
)
from app.models.stat_block import (
    StatBlockTemplate,
    StatValue,
    StatGauge,
    StatCollection,
)
from app.prompts.templates import (
    TEMPLATE_GENERATION_SYSTEM_PROMPT,
    GENERATE_CORE_STATS_INSTRUCTION,
    GENERATE_CONTAINERS_INSTRUCTION,
    ORGANIZE_LAYOUT_INSTRUCTION,
    IDENTIFY_MODES_INSTRUCTION,
    EXTRACT_PROCEDURE_INSTRUCTION,
    GENERATE_MECHANICS_INSTRUCTION,
)

logger = logging.getLogger(__name__)


class TemplateGenerationService:
    """
    Generates templates using the 5-step process with Flattened Layout.
    """

    def __init__(
        self,
        llm_connector: LLMConnector,
        rules_text: str,
        status_callback: Optional[Callable[[str], None]] = None,
    ):
        self.llm = llm_connector
        self.rules_text = rules_text
        self.status_callback = status_callback
        self.static_system_prompt = f"{TEMPLATE_GENERATION_SYSTEM_PROMPT}\n\n# RULES REFERENCE\n{self.rules_text}"

    def _update_status(self, message: str):
        if self.status_callback:
            self.status_callback(message)
        logger.info(f"[TemplateGen] {message}")

    def generate_template(self) -> Tuple[Ruleset, StatBlockTemplate]:
        # --- PRE-REQ ---
        self._update_status("Reading Ruleset Metadata...")

        class QuickMeta(BaseModel):
            name: str
            genre: str
            dice_notation: str
            roll_mechanic: str

        meta_res = self.llm.get_structured_response(
            self.static_system_prompt,
            [
                Message(
                    role="user",
                    content="Extract Game Name, Genre, and Core Dice Mechanics.",
                )
            ],
            QuickMeta,
        )

        ruleset = Ruleset(
            meta={"name": meta_res.name, "genre": meta_res.genre},
            physics=PhysicsConfig(
                dice_notation=meta_res.dice_notation,
                roll_mechanic=meta_res.roll_mechanic,
                success_condition="See Rules",
                crit_rules="See Rules",
            ),
        )

        # --- STEP 1: CORE STATS ---
        self._update_status("Phase 1: Defining Core Stats...")

        class CoreStatsDef(BaseModel):
            values: List[StatValue]
            gauges: List[StatGauge]

        core_res = self.llm.get_structured_response(
            self.static_system_prompt,
            [Message(role="user", content=GENERATE_CORE_STATS_INSTRUCTION.format(target_game=meta_res.name))],
            CoreStatsDef,
        )

        # --- STEP 2: CONTAINERS ---
        self._update_status("Phase 2: Defining Containers...")
        stats_summary = f"Defined Values: {[v.id for v in core_res.values]}\nDefined Gauges: {[g.id for g in core_res.gauges]}"

        class ContainerDef(BaseModel):
            collections: List[StatCollection]

        container_res = self.llm.get_structured_response(
            self.static_system_prompt,
            [
                Message(role="user", content=GENERATE_CORE_STATS_INSTRUCTION),
                Message(
                    role="assistant",
                    content=stats_summary,
                ),
                Message(role="user", content=GENERATE_CONTAINERS_INSTRUCTION.format(target_game=meta_res.name)),
            ],
            ContainerDef,
        )

        # --- STEP 3: LAYOUT (ASSIGNMENT) ---
        self._update_status("Phase 3: Assigning Panels...")

        # We ask the LLM to return the SAME lists, but with 'panel' and 'group' fields populated.
        # This acts as a "Refinement" pass.
        class LayoutAssignment(BaseModel):
            values: List[StatValue]
            gauges: List[StatGauge]
            collections: List[StatCollection]

        collections_summary = (
            f"Defined Collections: {[c.id for c in container_res.collections]}"
        )

        history_layout = [
            Message(role="user", content=GENERATE_CORE_STATS_INSTRUCTION),
            Message(role="assistant", content="Core Stats Defined."),
            Message(role="user", content=GENERATE_CONTAINERS_INSTRUCTION),
            Message(role="assistant", content=collections_summary),
            Message(role="user", content=ORGANIZE_LAYOUT_INSTRUCTION),
        ]

        # In this step, we expect the LLM to echo back the objects with updated panel/group fields
        layout_res = self.llm.get_structured_response(
            self.static_system_prompt, history_layout, LayoutAssignment
        )

        # --- STEP 4: PROCEDURES ---
        self._update_status("Phase 4: Extracting Game Logic...")

        class GameModes(BaseModel):
            names: List[str]

        # Use clean context for logic to avoid pollution from schema JSON
        logic_context = f"Target Game: {meta_res.name}\n"

        modes = self.llm.get_structured_response(
            self.static_system_prompt,
            [Message(role="user", content=logic_context + IDENTIFY_MODES_INSTRUCTION)],
            GameModes,
        )

        loops = GameLoopConfig()
        for mode in modes.names[:6] if modes else []:
            self._update_status(f"Extracting Procedure: {mode}...")
            try:
                proc = self.llm.get_structured_response(
                    self.static_system_prompt,
                    [
                        Message(
                            role="user",
                            content=logic_context
                            + EXTRACT_PROCEDURE_INSTRUCTION.format(mode_name=mode),
                        )
                    ],
                    ProcedureDef,
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
                logger.warning(f"Error extracting procedure: {e}")
                pass

        # --- STEP 5: MECHANICS ---
        self._update_status("Phase 5: Indexing Mechanics...")

        class MechDict(BaseModel):
            items: dict[str, RuleEntry]

        mech_res = self.llm.get_structured_response(
            self.static_system_prompt,
            [
                Message(
                    role="user", content=logic_context + GENERATE_MECHANICS_INSTRUCTION
                )
            ],
            MechDict,
        )

        # --- ASSEMBLY ---
        self._update_status("Finalizing Template...")

        ruleset = Ruleset(
            meta={"name": meta_res.name, "genre": meta_res.genre},
            physics=PhysicsConfig(
                dice_notation=meta_res.dice_notation,
                roll_mechanic=meta_res.roll_mechanic,
                success_condition="See Rules",
                crit_rules="See Rules",
            ),
            gameplay_procedures=loops,
            rules=mech_res.items,
        )

        # Convert Lists to Dicts for the Template
        # We use the output from Step 3 (LayoutAssignment) as it has the final panel data
        final_values = {v.id: v for v in layout_res.values}
        final_gauges = {g.id: g for g in layout_res.gauges}
        final_collections = {c.id: c for c in layout_res.collections}

        template = StatBlockTemplate(
            template_name=meta_res.name,
            values=final_values,
            gauges=final_gauges,
            collections=final_collections,
        )

        return ruleset, template
