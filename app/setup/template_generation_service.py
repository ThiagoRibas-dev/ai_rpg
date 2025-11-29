import logging
from typing import List, Callable, Optional, Tuple
from pydantic import BaseModel, create_model, Field

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
    DerivedStatDef,
    VitalResourceDef,
    ConsumableResourceDef,
    SkillDef,
    FeatureContainerDef,
    EquipmentConfig,
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
    """
    Generates game templates using the Refined Ontology.
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
        self.base_system_prompt = TEMPLATE_GENERATION_SYSTEM_PROMPT

    def _update_status(self, message: str):
        if self.status_callback:
            self.status_callback(message)
        logger.info(f"[TemplateGeneration] {message}")

    def _get_sys_prompt(self, game_name: str = "Unknown RPG"):
        return f"{self.base_system_prompt.format(game_name=game_name)}\n\n# GAME RULES TEXT\n{self.rules_text}"

    def generate_template(self) -> Tuple[Ruleset, StatBlockTemplate]:
        # --- PHASE 1: RULES KERNEL ---
        self._update_status("Identifying Game Identity...")

        temp_sys_prompt = f"{self.base_system_prompt.format(game_name='Unknown')}\n\n# RULES START\n{self.rules_text[:15000]}"

        class RulesetMeta(BaseModel):
            name: str
            genre: str
            description: str

        meta_res = self.llm.get_structured_response(
            system_prompt=temp_sys_prompt,
            chat_history=[Message(role="user", content=GENERATE_META_INSTRUCTION)],
            output_schema=RulesetMeta,
        )

        meta_data = {
            "name": meta_res.name if meta_res else "Untitled System",
            "genre": meta_res.genre if meta_res else "Generic",
            "description": meta_res.description if meta_res else "",
        }
        game_name = meta_data["name"]
        self._update_status(f"Analyzed: {game_name}")
        sys_prompt = self._get_sys_prompt(game_name)

        # Physics
        self._update_status("Defining Physics...")
        phys_res = self.llm.get_structured_response(
            system_prompt=sys_prompt,
            chat_history=[Message(role="user", content=GENERATE_PHYSICS_INSTRUCTION)],
            output_schema=PhysicsConfig,
        )

        # --- PHASE 2: STATBLOCK ---
        self._update_status("Analyzing Stats...")
        stat_analysis_gen = self.llm.get_streaming_response(
            sys_prompt, [Message(role="user", content=ANALYZE_STATBLOCK_INSTRUCTION)]
        )
        stat_analysis = "".join(stat_analysis_gen)
        context = f"*** STAT ANALYSIS ***\n{stat_analysis}\n\n"

        # Identity
        self._update_status("Defining Identity...")
        IdList = create_model(
            "IdList",
            items=(List[IdentityDef], Field(default_factory=list)),
            __base__=BaseModel,
        )
        id_res = self.llm.get_structured_response(
            sys_prompt,
            [Message(role="user", content=f"{context}{GENERATE_IDENTITY_INSTRUCTION}")],
            IdList,
        )

        # Fundamental Stats
        self._update_status("Defining Fundamental Stats...")
        FundList = create_model(
            "FundList",
            items=(List[FundamentalStatDef], Field(default_factory=list)),
            __base__=BaseModel,
        )
        fund_res = self.llm.get_structured_response(
            sys_prompt,
            [
                Message(
                    role="user", content=f"{context}{GENERATE_FUNDAMENTAL_INSTRUCTION}"
                )
            ],
            FundList,
        )

        # Variable Injection
        fund_names = [c.name for c in (fund_res.items if fund_res else [])]
        var_list = (
            ", ".join(fund_names) + ", " + ", ".join([f"{n}_Mod" for n in fund_names])
        )
        self._update_status(f"Variables: {var_list[:50]}...")

        # Derived
        self._update_status("Defining Derived Stats...")
        DerList = create_model(
            "DerList",
            items=(List[DerivedStatDef], Field(default_factory=list)),
            __base__=BaseModel,
        )
        prompt_der = GENERATE_DERIVED_INSTRUCTION.format(variable_list=var_list)
        der_res = self.llm.get_structured_response(
            sys_prompt,
            [Message(role="user", content=f"{context}{prompt_der}")],
            DerList,
        )

        if der_res and der_res.items:
            var_list += ", " + ", ".join([d.name for d in der_res.items])

        # Vitals
        self._update_status("Defining Vitals...")
        VitList = create_model(
            "VitList",
            items=(List[VitalResourceDef], Field(default_factory=list)),
            __base__=BaseModel,
        )
        prompt_vit = GENERATE_VITALS_INSTRUCTION.format(variable_list=var_list)
        vit_res = self.llm.get_structured_response(
            sys_prompt,
            [Message(role="user", content=f"{context}{prompt_vit}")],
            VitList,
        )

        # Consumables
        self._update_status("Defining Consumables...")
        ConList = create_model(
            "ConList",
            items=(List[ConsumableResourceDef], Field(default_factory=list)),
            __base__=BaseModel,
        )
        con_res = self.llm.get_structured_response(
            sys_prompt,
            [
                Message(
                    role="user", content=f"{context}{GENERATE_CONSUMABLES_INSTRUCTION}"
                )
            ],
            ConList,
        )

        # Skills
        self._update_status("Defining Skills...")
        SkillList = create_model(
            "SkillList",
            items=(List[SkillDef], Field(default_factory=list)),
            __base__=BaseModel,
        )
        skill_res = self.llm.get_structured_response(
            sys_prompt,
            [Message(role="user", content=f"{context}{GENERATE_SKILLS_INSTRUCTION}")],
            SkillList,
        )

        # Features
        self._update_status("Defining Feature Buckets...")
        FeatList = create_model(
            "FeatList",
            items=(List[FeatureContainerDef], Field(default_factory=list)),
            __base__=BaseModel,
        )
        feat_res = self.llm.get_structured_response(
            sys_prompt,
            [Message(role="user", content=f"{context}{GENERATE_FEATURES_INSTRUCTION}")],
            FeatList,
        )

        # Equipment
        self._update_status("Defining Equipment...")
        eq_res = self.llm.get_structured_response(
            sys_prompt,
            [
                Message(
                    role="user", content=f"{context}{GENERATE_EQUIPMENT_INSTRUCTION}"
                )
            ],
            EquipmentConfig,
        )

        stat_template = StatBlockTemplate(
            template_name=game_name + " Character",
            identity_categories=id_res.items if id_res else [],
            fundamental_stats=fund_res.items if fund_res else [],
            derived_stats=der_res.items if der_res else [],
            vital_resources=vit_res.items if vit_res else [],
            consumable_resources=con_res.items if con_res else [],
            skills=skill_res.items if skill_res else [],
            features=feat_res.items if feat_res else [],
            equipment=eq_res if eq_res else EquipmentConfig(),
        )

        # --- PHASE 3: MODES ---
        self._update_status("Identifying Game Modes...")

        class GameModes(BaseModel):
            names: List[str]

        modes_res = self.llm.get_structured_response(
            sys_prompt,
            [Message(role="user", content=IDENTIFY_MODES_INSTRUCTION)],
            GameModes,
        )

        loops = GameLoopConfig()
        detected_modes = modes_res.names[:5] if modes_res else []

        for mode in detected_modes:
            self._update_status(f"Extracting Procedure: {mode}...")
            try:
                prompt = EXTRACT_PROCEDURE_INSTRUCTION.format(mode_name=mode)
                proc_def = self.llm.get_structured_response(
                    sys_prompt, [Message(role="user", content=prompt)], ProcedureDef
                )

                # Map to schema fields if match
                m_lower = mode.lower()
                if "combat" in m_lower:
                    loops.combat = proc_def
                elif "exploration" in m_lower:
                    loops.exploration = proc_def
                elif "social" in m_lower:
                    loops.social = proc_def
                elif "downtime" in m_lower:
                    loops.downtime = proc_def
                # TWEAK: Use renamed field
                else:
                    loops.general_procedures.append(proc_def)

            except Exception:
                pass

        # Mechanics (RAG)
        self._update_status("Extracting Mechanics...")

        class MechanicsOutput(BaseModel):
            rules: List[RuleEntry]

        mech_res = self.llm.get_structured_response(
            system_prompt=sys_prompt,
            chat_history=[Message(role="user", content=GENERATE_MECHANICS_INSTRUCTION)],
            output_schema=MechanicsOutput,
        )

        ruleset = Ruleset(
            meta=meta_data,
            physics=phys_res,
            gameplay_loops=loops,
            mechanics=mech_res.rules if mech_res else [],
        )

        return ruleset, stat_template
