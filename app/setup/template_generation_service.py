import logging
from typing import List, Callable, Optional, Tuple, Literal
from pydantic import BaseModel, Field, create_model

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
    StatTrack,
    StatCollection,
)
from app.prompts.templates import (
    TEMPLATE_GENERATION_SYSTEM_PROMPT,
    GENERATE_FUNDAMENTALS_INSTRUCTION,
    GENERATE_CONTAINERS_INSTRUCTION,
    GENERATE_DERIVED_INSTRUCTION,
    ORGANIZE_LAYOUT_INSTRUCTION,
    IDENTIFY_MODES_INSTRUCTION,
    EXTRACT_PROCEDURE_INSTRUCTION,
    GENERATE_MECHANICS_INSTRUCTION,
)

logger = logging.getLogger(__name__)


class LayoutEntry(BaseModel):
    panel: Literal[
        "header", "sidebar", "main", "equipment", "skills", "spells", "notes"
    ]
    group: str


class TemplateGenerationService:
    def __init__(
        self,
        llm_connector: LLMConnector,
        rules_text: str,
        status_callback: Optional[Callable[[str], None]] = None,
    ):
        self.llm = llm_connector
        self.rules_text = rules_text
        self.status_callback = status_callback
        # We delay formatting the system prompt until we have the game name
        self.raw_system_prompt = f"{TEMPLATE_GENERATION_SYSTEM_PROMPT}\n\n# RULES REFERENCE\n{self.rules_text}"

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

        # Initial probe to get the name
        meta_res = self.llm.get_structured_response(
            self.raw_system_prompt,
            [
                Message(
                    role="user",
                    content="Extract Game Name, Genre, and Core Dice Mechanics.",
                )
            ],
            QuickMeta,
        )

        # Now we have the name, we lock in the System Prompt
        game_name = meta_res.name
        system_prompt = self.raw_system_prompt.format(target_game=game_name)

        ruleset = Ruleset(
            meta={"name": game_name, "genre": meta_res.genre},
            physics=PhysicsConfig(
                dice_notation=meta_res.dice_notation,
                roll_mechanic=meta_res.roll_mechanic,
                success_condition="See Rules",
                crit_rules="See Rules",
            ),
        )

        # --- STEP 1: FUNDAMENTALS (Inputs) ---
        self._update_status("Phase 1: Defining Fundamentals...")

        class FundamentalsDef(BaseModel):
            fundamentals: List[StatValue]

        fund_res = self.llm.get_structured_response(
            system_prompt,
            [
                Message(
                    role="user",
                    content=GENERATE_FUNDAMENTALS_INSTRUCTION.format(
                        target_game=game_name
                    ),
                )
            ],
            FundamentalsDef,
        )

        fund_ids = [v.id for v in fund_res.fundamentals]
        fund_summary = f"Defined Fundamentals: {fund_ids}"

        # --- STEP 2: COLLECTIONS (Lists) ---
        self._update_status("Phase 2: Defining Collections...")

        class ContainerDef(BaseModel):
            collections: List[StatCollection]

        coll_res = self.llm.get_structured_response(
            system_prompt,
            [
                Message(
                    role="user",
                    content=GENERATE_FUNDAMENTALS_INSTRUCTION.format(
                        target_game=game_name
                    ),
                ),
                Message(role="assistant", content=fund_summary),
                Message(
                    role="user",
                    content=GENERATE_CONTAINERS_INSTRUCTION.format(
                        target_game=game_name
                    ),
                ),
            ],
            ContainerDef,
        )

        coll_ids = [c.id for c in coll_res.collections]
        coll_summary = f"Defined Collections: {coll_ids}"

        # --- STEP 3: DERIVED & GAUGES (Outputs) ---
        self._update_status("Phase 3: Defining Derived Stats...")

        class DerivedDef(BaseModel):
            derived: List[StatValue]
            gauges: List[StatGauge]
            tracks: List[StatTrack]

        derived_prompt = GENERATE_DERIVED_INSTRUCTION.format(
            target_game=game_name,
            fundamentals_list=fund_summary,
            collections_list=coll_summary,
        )

        derived_res = self.llm.get_structured_response(
            system_prompt,
            [
                Message(
                    role="user",
                    content=GENERATE_FUNDAMENTALS_INSTRUCTION.format(
                        target_game=game_name
                    ),
                ),
                Message(role="assistant", content=fund_summary),
                Message(
                    role="user",
                    content=GENERATE_CONTAINERS_INSTRUCTION.format(
                        target_game=game_name
                    ),
                ),
                Message(role="assistant", content=coll_summary),
                Message(role="user", content=derived_prompt),
            ],
            DerivedDef,
        )

        # --- STEP 4: LAYOUT (DYNAMIC PATCHING) ---
        self._update_status("Phase 4: Assigning Panels...")

        all_ids = []
        all_ids.extend(fund_ids)
        all_ids.extend([d.id for d in derived_res.derived])
        all_ids.extend([g.id for g in derived_res.gauges])
        all_ids.extend(coll_ids)

        field_definitions = {}
        for item_id in all_ids:
            safe_field_name = f"field_{item_id}"
            field_definitions[safe_field_name] = (
                LayoutEntry,
                Field(..., alias=item_id),
            )

        DynamicLayoutMap = create_model("DynamicLayoutMap", **field_definitions)

        layout_prompt = ORGANIZE_LAYOUT_INSTRUCTION.format(
            target_game=game_name, stat_list=", ".join(all_ids)
        )

        layout_map = self.llm.get_structured_response(
            system_prompt,
            [Message(role="user", content=layout_prompt)],
            DynamicLayoutMap,
        )

        layout_dict = layout_map.model_dump(by_alias=True)

        # Helper to apply layout
        def apply_layout(items):
            for item in items:
                if item.id in layout_dict:
                    item.panel = layout_dict[item.id]["panel"]
                    item.group = layout_dict[item.id]["group"]

        apply_layout(fund_res.fundamentals)
        apply_layout(derived_res.derived)
        apply_layout(derived_res.gauges)
        apply_layout(coll_res.collections)

        # --- STEP 5: PROCEDURES ---
        self._update_status("Phase 5: Extracting Game Logic...")

        class GameModes(BaseModel):
            names: List[str]

        # Logic Context needs game name
        logic_context = f"Target Game: {game_name}\n"

        modes = self.llm.get_structured_response(
            system_prompt,
            [Message(role="user", content=logic_context + IDENTIFY_MODES_INSTRUCTION)],
            GameModes,
        )

        loops = GameLoopConfig()
        for mode in modes.names[:6] if modes else []:
            self._update_status(f"Extracting Procedure: {mode}...")
            try:
                proc = self.llm.get_structured_response(
                    system_prompt,
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
                logger.warning(f"Failed to parse game modes: {e}")
                pass

        # --- STEP 6: MECHANICS ---
        self._update_status("Phase 6: Indexing Mechanics...")

        class MechDict(BaseModel):
            items: dict[str, RuleEntry]

        mech_res = self.llm.get_structured_response(
            system_prompt,
            [
                Message(
                    role="user", content=logic_context + GENERATE_MECHANICS_INSTRUCTION
                )
            ],
            MechDict,
        )

        # --- ASSEMBLY ---
        # Note: We now have the correct game name in meta
        ruleset = Ruleset(
            meta={"name": game_name, "genre": meta_res.genre},
            physics=PhysicsConfig(
                dice_notation=meta_res.dice_notation,
                roll_mechanic=meta_res.roll_mechanic,
                success_condition="See Rules",
                crit_rules="See Rules",
            ),
            gameplay_procedures=loops,
            rules=mech_res.items,
        )

        template = StatBlockTemplate(
            template_name=game_name,
            fundamentals={v.id: v for v in fund_res.fundamentals},
            derived={v.id: v for v in derived_res.derived},
            gauges={g.id: g for g in derived_res.gauges},
            collections={c.id: c for c in coll_res.collections},
        )

        return ruleset, template
