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
    IdentityDef,
    FundamentalStatDef,
    VitalResourceDef,
    ConsumableResourceDef,
    FeatureContainerDef,
    EquipmentConfig,
    SkillValue,
)
from app.prompts.templates import (
    TEMPLATE_GENERATION_SYSTEM_PROMPT,
    GENERATE_META_INSTRUCTION,
    GENERATE_PHYSICS_INSTRUCTION,
    ANALYZE_STATBLOCK_INSTRUCTION,
    GENERATE_IDENTITY_INSTRUCTION,
    GENERATE_FUNDAMENTAL_INSTRUCTION,
    GENERATE_DERIVED_INSTRUCTION,
    GENERATE_VITALS_INSTRUCTION,
    GENERATE_CONSUMABLES_INSTRUCTION,
    GENERATE_SKILLS_INSTRUCTION,
    GENERATE_FEATURES_INSTRUCTION,
    GENERATE_EQUIPMENT_INSTRUCTION,
    IDENTIFY_MODES_INSTRUCTION,
    EXTRACT_PROCEDURE_INSTRUCTION,
    GENERATE_MECHANICS_INSTRUCTION,
)

logger = logging.getLogger(__name__)


class TemplateGenerationService:
    """Generates optimized dict-based templates with prompt caching efficiency."""

    def __init__(
        self,
        llm_connector: LLMConnector,
        rules_text: str,
        status_callback: Optional[Callable[[str], None]] = None,
    ):
        self.llm = llm_connector
        self.rules_text = rules_text
        self.status_callback = status_callback

        self.static_system_prompt = f"{TEMPLATE_GENERATION_SYSTEM_PROMPT}\n\n# RULES TEXT\n{self.rules_text}"

    def _update_status(self, message: str):
        if self.status_callback:
            self.status_callback(message)
        logger.info(f"[TemplateGen] {message}")

    def generate_template(self) -> Tuple[Ruleset, StatBlockTemplate]:
        # --- 1. META & PHYSICS ---
        self._update_status("Identifying Identity...")

        class RulesetMeta(BaseModel):
            name: str
            genre: str
            description: str

        # CACHE HIT 1: We use the full static prompt immediately.
        # Ideally, this processes the rules once, and all subsequent calls reuse the KV cache.
        meta_res = self.llm.get_structured_response(
            self.static_system_prompt,
            [Message(role="user", content=GENERATE_META_INSTRUCTION)],
            RulesetMeta,
        )

        meta_data = {
            "name": meta_res.name,
            "genre": meta_res.genre,
            "description": meta_res.description,
        }

        # Inject Game Name into Context for future steps (User Side)
        game_context = f"Target Game: {meta_res.name}\n"
        self._update_status(f"Analyzed: {meta_res.name}")

        self._update_status("Defining Physics...")
        # CACHE HIT 2: Same system prompt
        phys_res = self.llm.get_structured_response(
            self.static_system_prompt,
            [Message(role="user", content=game_context + GENERATE_PHYSICS_INSTRUCTION)],
            PhysicsConfig,
        )

        # --- 2. STATBLOCK (DICTS) ---
        self._update_status("Analyzing Stats...")
        # CACHE HIT 3
        stat_gen = self.llm.get_streaming_response(
            self.static_system_prompt,
            [
                Message(
                    role="user", content=game_context + ANALYZE_STATBLOCK_INSTRUCTION
                )
            ],
        )
        analysis_text = "".join(stat_gen)

        # Accumulate context.
        # Note: Adding 'analysis_text' to the User Prompt will slightly degrade cache performance
        # for subsequent steps compared to keeping the User Prompt static,
        # but it is necessary for logic. The SYSTEM prompt (the heavy part) remains cached.
        context = f"{game_context}*** ANALYSIS ***\n{analysis_text}\n\n"

        # Wrappers for Dict responses
        class IdDict(BaseModel):
            items: dict[str, IdentityDef]

        class FundDict(BaseModel):
            items: dict[str, FundamentalStatDef]

        class DerDict(BaseModel):
            items: dict[str, str]

        class VitDict(BaseModel):
            items: dict[str, VitalResourceDef]

        class ConDict(BaseModel):
            items: dict[str, ConsumableResourceDef]

        class SkillDict(BaseModel):
            items: dict[str, SkillValue]

        class FeatDict(BaseModel):
            items: dict[str, FeatureContainerDef]

        self._update_status("Defining Identity...")
        id_res = self.llm.get_structured_response(
            self.static_system_prompt,
            [Message(role="user", content=context + GENERATE_IDENTITY_INSTRUCTION)],
            IdDict,
        )

        self._update_status("Defining Fundamentals...")
        fund_res = self.llm.get_structured_response(
            self.static_system_prompt,
            [Message(role="user", content=context + GENERATE_FUNDAMENTAL_INSTRUCTION)],
            FundDict,
        )

        var_list = (
            ", ".join(fund_res.items.keys())
            + ", "
            + ", ".join([f"{k}_Mod" for k in fund_res.items.keys()])
        )

        self._update_status("Defining Derived...")
        prompt_der = GENERATE_DERIVED_INSTRUCTION.format(variable_list=var_list)
        der_res = self.llm.get_structured_response(
            self.static_system_prompt,
            [Message(role="user", content=context + prompt_der)],
            DerDict,
        )

        if der_res.items:
            var_list += ", " + ", ".join(der_res.items.keys())

        self._update_status("Defining Vitals...")
        prompt_vit = GENERATE_VITALS_INSTRUCTION.format(variable_list=var_list)
        vit_res = self.llm.get_structured_response(
            self.static_system_prompt,
            [Message(role="user", content=context + prompt_vit)],
            VitDict,
        )

        self._update_status("Defining Consumables...")
        con_res = self.llm.get_structured_response(
            self.static_system_prompt,
            [Message(role="user", content=context + GENERATE_CONSUMABLES_INSTRUCTION)],
            ConDict,
        )

        self._update_status("Defining Skills...")
        skill_res = self.llm.get_structured_response(
            self.static_system_prompt,
            [Message(role="user", content=context + GENERATE_SKILLS_INSTRUCTION)],
            SkillDict,
        )

        self._update_status("Defining Features...")
        feat_res = self.llm.get_structured_response(
            self.static_system_prompt,
            [Message(role="user", content=context + GENERATE_FEATURES_INSTRUCTION)],
            FeatDict,
        )

        self._update_status("Defining Equipment...")
        eq_res = self.llm.get_structured_response(
            self.static_system_prompt,
            [Message(role="user", content=context + GENERATE_EQUIPMENT_INSTRUCTION)],
            EquipmentConfig,
        )

        stat_template = StatBlockTemplate(
            template_name=meta_res.name + " Character",
            identity_categories=id_res.items,
            fundamental_stats=fund_res.items,
            derived_stats=der_res.items,
            vital_resources=vit_res.items,
            consumable_resources=con_res.items,
            skills=skill_res.items,
            features=feat_res.items,
            equipment=eq_res,
        )

        # --- 3. PROCEDURES ---
        self._update_status("Identifying Modes...")

        class GameModes(BaseModel):
            names: List[str]

        # CACHE HIT: Still using self.static_system_prompt
        modes = self.llm.get_structured_response(
            self.static_system_prompt,
            [Message(role="user", content=game_context + IDENTIFY_MODES_INSTRUCTION)],
            GameModes,
        )

        loops = GameLoopConfig()
        for mode in modes.names[:5] if modes else []:
            self._update_status(f"Extracting {mode}...")
            try:
                proc = self.llm.get_structured_response(
                    self.static_system_prompt,
                    [
                        Message(
                            role="user",
                            content=game_context
                            + EXTRACT_PROCEDURE_INSTRUCTION.format(mode_name=mode),
                        )
                    ],
                    ProcedureDef,
                )
                m = mode.lower()
                if "combat" in m:
                    loops.combat = proc
                elif "exploration" in m:
                    loops.exploration = proc
                elif "social" in m:
                    loops.social = proc
                elif "downtime" in m:
                    loops.downtime = proc
                else:
                    loops.general_procedures[mode] = proc
            except Exception as e:
                logger.warning(f"Error extracting {mode}: {e}")
                pass

        # --- 4. MECHANICS (RAG) ---
        self._update_status("Extracting Mechanics...")

        class MechDict(BaseModel):
            items: dict[str, RuleEntry]

        mech_res = self.llm.get_structured_response(
            self.static_system_prompt,
            [
                Message(
                    role="user", content=game_context + GENERATE_MECHANICS_INSTRUCTION
                )
            ],
            MechDict,
        )

        ruleset = Ruleset(
            meta=meta_data,
            physics=phys_res,
            gameplay_loops=loops,
            mechanics=mech_res.items,
        )

        return ruleset, stat_template
