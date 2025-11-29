import os

FILES = {}

# ==============================================================================
# 1. MODELS: RULESET (Updated to Dicts + Field Renames)
# ==============================================================================
FILES["app/models/ruleset.py"] = """\"\"\"
Models for the Game System Rules.
Optimized for Token Efficiency with Rich Descriptions.
\"\"\"

from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class RuleEntry(BaseModel):
    \"\"\"Atomic rule for RAG.\"\"\"
    text: str = Field(..., description="The concise text of this rule entry.")
    tags: List[str] = Field(
        default_factory=list,
        description="Keywords to find this rule entry (e.g. 'combat', 'stealth', 'magic').",
    )


class PhysicsConfig(BaseModel):
    \"\"\"The Resolution Engine.\"\"\"
    dice_notation: str = Field(
        ...,
        description="The standard formula used for dice rolls in this system (e.g. '1d20', '3d6', 'd100', etc).",
    )
    roll_mechanic: str = Field(
        ...,
        description="Instructions on how to resolve a roll using the dice notation (e.g. 'Roll + Mod vs DC', 'Roll under Skill', 'Count successes', etc).",
    )
    success_condition: str = Field(
        ...,
        description="The condition required to count a roll as a success (e.g. 'Result >= Target Number', 'At least 1 six', etc).",
    )
    crit_rules: str = Field(
        ...,
        description="Rules describing what happens on a critical success or failure(e.g. 'Nat 20 / Nat 1', '10 over / 10 under DC', etc).",
    )


class ProcedureDef(BaseModel):
    \"\"\"A specific game loop.\"\"\"
    description: str = Field(
        ...,
        description="A summary of the conflict or activity this procedure resolves.",
    )
    steps: List[str] = Field(
        default_factory=list,
        description="The sequential list of actions required to complete this procedure.",
    )


class GameLoopConfig(BaseModel):
    \"\"\"Procedures grouped by mode. Each category can hold multiple specific procedures.\"\"\"

    encounter: dict[str, ProcedureDef] = Field(
        default_factory=dict,
        description="Procedures for resolving encounters (Standard Combat, Duels, Chases, Netrunning).",
    )

    exploration: dict[str, ProcedureDef] = Field(
        default_factory=dict,
        description="Procedures for navigating the environment (Dungeon Crawl, Hex Travel, Investigation).",
    )

    social: dict[str, ProcedureDef] = Field(
        default_factory=dict,
        description="Procedures for influencing NPCs (Persuasion, Intimidation, Bartering, Interrogation).",
    )

    downtime: dict[str, ProcedureDef] = Field(
        default_factory=dict,
        description="Procedures for resting and recovery (Camping, Crafting, Training, Level Up).",
    )

    misc: dict[str, ProcedureDef] = Field(
        default_factory=dict,
        description="Other specific procedures found in the rules that don't fit above.",
    )


class Ruleset(BaseModel):
    \"\"\"Root Configuration.\"\"\"

    meta: Dict[str, str] = Field(
        default_factory=lambda: {"name": "Untitled", "genre": "Generic"}
    )

    physics: PhysicsConfig = Field(
        ..., description="The core engine rules for dice and resolution."
    )

    # Renamed from 'mechanics' to 'rules' per request
    rules: dict[str, RuleEntry] = Field(
        default_factory=dict,
        description="The dictionary of specific rule entries.",
    )

    # Renamed from 'gameplay_loops' to 'gameplay_procedures' per request
    gameplay_procedures: GameLoopConfig = Field(
        default_factory=GameLoopConfig,
        description="The structured procedures for handling different game modes.",
    )
"""

# ==============================================================================
# 2. SCAFFOLDING (Updated to populate new Dict fields)
# ==============================================================================
FILES["app/setup/scaffolding.py"] = """import json
import logging
from app.models.ruleset import Ruleset, PhysicsConfig, GameLoopConfig, ProcedureDef
from app.models.stat_block import (
    StatBlockTemplate, IdentityDef, FundamentalStatDef, VitalResourceDef, 
    EquipmentConfig, BodySlotDef
)
from app.setup.setup_manifest import SetupManifest

logger = logging.getLogger(__name__)

def _get_default_scaffolding():
    \"\"\"Returns default Refined scaffolding.\"\"\"
    ruleset = Ruleset(
        meta={"name": "Default System", "genre": "Generic"},
        physics=PhysicsConfig(
            dice_notation="1d20",
            roll_mechanic="Roll + Mod vs DC",
            success_condition="Result >= Target Number",
            crit_rules="Nat 20 = Critical Success"
        ),
        gameplay_procedures=GameLoopConfig(
            encounter={
                "Standard Combat": ProcedureDef(description="Turn Based Combat", steps=["Roll Initiative", "Take Turns", "Resolve Actions"])
            },
            exploration={
                "Freeform": ProcedureDef(description="General Exploration", steps=["Describe Scene", "Player Action", "Result"])
            }
        )
    )
    
    template = StatBlockTemplate(
        template_name="Adventurer",
        identity_categories={"Class": IdentityDef(value_type="selection")},
        fundamental_stats={
            "Strength": FundamentalStatDef(default=10),
            "Agility": FundamentalStatDef(default=10)
        },
        vital_resources={"HP": VitalResourceDef(max_formula="10", on_zero="Unconscious")},
        equipment=EquipmentConfig(slots={
            "Main Hand": ["Weapon"],
            "Body": ["Armor"]
        })
    )
    return ruleset, template

def inject_setup_scaffolding(session_id: int, prompt_manifest_json: str, db_manager):
    \"\"\"Injects scaffolding using Refined Models.\"\"\"
    ruleset_model = None
    st_model = None

    if prompt_manifest_json and prompt_manifest_json != "{}":
        try:
            data = json.loads(prompt_manifest_json)
            if data.get("ruleset"): ruleset_model = Ruleset(**data["ruleset"])
            if data.get("stat_template"): st_model = StatBlockTemplate(**data["stat_template"])
        except Exception as e:
            logger.error(f"Manifest parse error: {e}. Using defaults.")

    if not ruleset_model or not st_model:
        ruleset_model, st_model = _get_default_scaffolding()

    ruleset_model.meta["name"] = f"{ruleset_model.meta.get('name', 'Untitled')} (Session {session_id})"
    
    try:
        rs_id = db_manager.rulesets.create(ruleset_model)
        st_id = db_manager.stat_templates.create(rs_id, st_model)
        
        try:
            from app.core.vector_store import VectorStore
            vs = VectorStore()
            rule_dicts = []
            # Updated to use 'rules' field instead of 'mechanics'
            for name, rule in ruleset_model.rules.items():
                d = rule.model_dump()
                d['name'] = name 
                rule_dicts.append(d)
            vs.add_rules(rs_id, rule_dicts)
        except Exception as e:
            logger.error(f"Failed to index initial rules: {e}")

        manifest_mgr = SetupManifest(db_manager)
        manifest_mgr.update_manifest(session_id, {
            "ruleset_id": rs_id, 
            "stat_template_id": st_id,
            "genre": ruleset_model.meta.get("genre", "Generic"),
            "tone": ruleset_model.meta.get("tone", "Neutral")
        })

        # Initialize Player Data
        fund_stats = {a.name: a.default for a in st_model.fundamental_stats.values()}
        
        vitals = {}
        for name, m in st_model.vital_resources.items():
            vitals[name] = {"current": 10, "max": 10}
            
        consumables = {}
        for name, m in st_model.consumable_resources.items():
            consumables[name] = {"current": 0, "max": 0}

        skills = {s: 0 for s in st_model.skills.keys()}
        features = {f: [] for f in st_model.features.keys()}

        player_data = {
            "name": "Player",
            "template_id": st_id,
            "identity": {},
            "fundamental_stats": fund_stats,
            "vital_resources": vitals,
            "consumable_resources": consumables,
            "skills": skills,
            "features": features,
            "equipment": {"inventory": [], "equipped": {}},
            "derived_stats": {} 
        }

        db_manager.game_state.set_entity(session_id, "character", "player", player_data)
        
    except Exception as e:
        logger.error(f"Error during scaffolding injection: {e}", exc_info=True)
"""

# ==============================================================================
# 3. GENERATION SERVICE (Logic to populate the dicts)
# ==============================================================================
FILES["app/setup/template_generation_service.py"] = """import logging
from typing import List, Callable, Optional, Tuple, Dict, Union
from pydantic import BaseModel, create_model, Field

from app.llm.llm_connector import LLMConnector
from app.models.message import Message
from app.models.ruleset import Ruleset, PhysicsConfig, GameLoopConfig, ProcedureDef, RuleEntry
from app.models.stat_block import (
    StatBlockTemplate, IdentityDef, FundamentalStatDef, DerivedStatDef, 
    VitalResourceDef, ConsumableResourceDef, SkillDef, FeatureContainerDef, EquipmentConfig, SkillValue
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
    GENERATE_MECHANICS_INSTRUCTION
)

logger = logging.getLogger(__name__)

class TemplateGenerationService:
    \"\"\"Generates optimized dict-based templates with prompt caching efficiency.\"\"\"

    def __init__(self, llm_connector: LLMConnector, rules_text: str, status_callback: Optional[Callable[[str], None]] = None):
        self.llm = llm_connector
        self.rules_text = rules_text
        self.status_callback = status_callback
        
        base_clean = TEMPLATE_GENERATION_SYSTEM_PROMPT.split("**{game_name}**")[0] + "the provided rules text."
        self.static_system_prompt = f"{base_clean}\\n\\n# RULES TEXT\\n{self.rules_text}"

    def _update_status(self, message: str):
        if self.status_callback: self.status_callback(message)
        logger.info(f"[TemplateGen] {message}")

    def generate_template(self) -> Tuple[Ruleset, StatBlockTemplate]:
        
        # --- 1. META & PHYSICS ---
        self._update_status("Identifying Identity...")
        class RulesetMeta(BaseModel):
            name: str
            genre: str
            description: str

        meta_res = self.llm.get_structured_response(
            self.static_system_prompt, 
            [Message(role="user", content=GENERATE_META_INSTRUCTION)], 
            RulesetMeta
        )
        
        meta_data = {"name": meta_res.name, "genre": meta_res.genre, "description": meta_res.description}
        game_context = f"Target Game: {meta_res.name}\\n"
        self._update_status(f"Analyzed: {meta_res.name}")

        self._update_status("Defining Physics...")
        phys_res = self.llm.get_structured_response(
            self.static_system_prompt, 
            [Message(role="user", content=game_context + GENERATE_PHYSICS_INSTRUCTION)], 
            PhysicsConfig
        )

        # --- 2. STATBLOCK (DICTS) ---
        self._update_status("Analyzing Stats...")
        stat_gen = self.llm.get_streaming_response(
            self.static_system_prompt, 
            [Message(role="user", content=game_context + ANALYZE_STATBLOCK_INSTRUCTION)]
        )
        analysis_text = "".join(stat_gen)
        context = f"{game_context}*** ANALYSIS ***\\n{analysis_text}\\n\\n"

        class IdDict(BaseModel): items: dict[str, IdentityDef]
        class FundDict(BaseModel): items: dict[str, FundamentalStatDef]
        class DerDict(BaseModel): items: dict[str, str]
        class VitDict(BaseModel): items: dict[str, VitalResourceDef]
        class ConDict(BaseModel): items: dict[str, ConsumableResourceDef]
        class SkillDict(BaseModel): items: dict[str, SkillValue]
        class FeatDict(BaseModel): items: dict[str, FeatureContainerDef]

        self._update_status("Defining Identity...")
        id_res = self.llm.get_structured_response(self.static_system_prompt, [Message(role="user", content=context+GENERATE_IDENTITY_INSTRUCTION)], IdDict)

        self._update_status("Defining Fundamentals...")
        fund_res = self.llm.get_structured_response(self.static_system_prompt, [Message(role="user", content=context+GENERATE_FUNDAMENTAL_INSTRUCTION)], FundDict)
        
        var_list = ", ".join(fund_res.items.keys()) + ", " + ", ".join([f"{k}_Mod" for k in fund_res.items.keys()])

        self._update_status("Defining Derived...")
        prompt_der = GENERATE_DERIVED_INSTRUCTION.format(variable_list=var_list)
        der_res = self.llm.get_structured_response(self.static_system_prompt, [Message(role="user", content=context+prompt_der)], DerDict)
        
        if der_res.items: var_list += ", " + ", ".join(der_res.items.keys())

        self._update_status("Defining Vitals...")
        prompt_vit = GENERATE_VITALS_INSTRUCTION.format(variable_list=var_list)
        vit_res = self.llm.get_structured_response(self.static_system_prompt, [Message(role="user", content=context+prompt_vit)], VitDict)

        self._update_status("Defining Consumables...")
        con_res = self.llm.get_structured_response(self.static_system_prompt, [Message(role="user", content=context+GENERATE_CONSUMABLES_INSTRUCTION)], ConDict)

        self._update_status("Defining Skills...")
        skill_res = self.llm.get_structured_response(self.static_system_prompt, [Message(role="user", content=context+GENERATE_SKILLS_INSTRUCTION)], SkillDict)

        self._update_status("Defining Features...")
        feat_res = self.llm.get_structured_response(self.static_system_prompt, [Message(role="user", content=context+GENERATE_FEATURES_INSTRUCTION)], FeatDict)

        self._update_status("Defining Equipment...")
        eq_res = self.llm.get_structured_response(self.static_system_prompt, [Message(role="user", content=context+GENERATE_EQUIPMENT_INSTRUCTION)], EquipmentConfig)

        stat_template = StatBlockTemplate(
            template_name=meta_res.name + " Character",
            identity_categories=id_res.items,
            fundamental_stats=fund_res.items,
            derived_stats=der_res.items,
            vital_resources=vit_res.items,
            consumable_resources=con_res.items,
            skills=skill_res.items,
            features=feat_res.items,
            equipment=eq_res
        )

        # --- 3. PROCEDURES ---
        self._update_status("Identifying Modes...")
        class GameModes(BaseModel): names: List[str]
        modes = self.llm.get_structured_response(self.static_system_prompt, [Message(role="user", content=game_context+IDENTIFY_MODES_INSTRUCTION)], GameModes)
        
        loops = GameLoopConfig()
        
        for mode in (modes.names[:6] if modes else []):
            self._update_status(f"Extracting {mode}...")
            try:
                proc = self.llm.get_structured_response(self.static_system_prompt, [Message(role="user", content=game_context+EXTRACT_PROCEDURE_INSTRUCTION.format(mode_name=mode))], ProcedureDef)
                m = mode.lower()
                
                # Logic to assign to correct dictionary
                if "combat" in m or "encounter" in m or "battle" in m: 
                    loops.encounter[mode] = proc
                elif "exploration" in m or "travel" in m: 
                    loops.exploration[mode] = proc
                elif "social" in m or "interact" in m: 
                    loops.social[mode] = proc
                elif "downtime" in m or "rest" in m or "camp" in m: 
                    loops.downtime[mode] = proc
                else: 
                    loops.misc[mode] = proc
            except: pass

        # --- 4. MECHANICS (RAG) ---
        self._update_status("Extracting Mechanics...")
        class MechDict(BaseModel): items: dict[str, RuleEntry]
        mech_res = self.llm.get_structured_response(self.static_system_prompt, [Message(role="user", content=game_context+GENERATE_MECHANICS_INSTRUCTION)], MechDict)

        ruleset = Ruleset(
            meta=meta_data,
            physics=phys_res,
            gameplay_procedures=loops, # Updated field name
            rules=mech_res.items       # Updated field name
        )

        return ruleset, stat_template
"""

# ==============================================================================
# 4. CONTEXT BUILDER (Render multiple procedures)
# ==============================================================================
FILES["app/context/context_builder.py"] = """import logging
import math
from typing import List, Dict
from app.models.session import Session
from app.models.game_session import GameSession
from app.models.message import Message
from app.setup.setup_manifest import SetupManifest


class ContextBuilder:
    \"\"\"
    Builds context using the Refined Schema.
    \"\"\"

    def __init__(
        self,
        db_manager,
        vector_store,
        state_builder,
        mem_retriever,
        simulation_service,
        logger: logging.Logger | None = None,
    ):
        self.db = db_manager
        self.vs = vector_store
        self.state_builder = state_builder
        self.mem_retriever = mem_retriever
        self.simulation_service = simulation_service
        self.logger = logger or logging.getLogger(__name__)

    def build_static_system_instruction(
        self,
        game_session: GameSession,
        ruleset_text: str = "", 
    ) -> str:
        sections = []
        session_data = Session.from_json(game_session.session_data)
        user_game_prompt = session_data.get_system_prompt()
        sections.append(user_game_prompt)

        # Kernel (Physics)
        manifest = SetupManifest(self.db).get_manifest(game_session.id)
        ruleset_id = manifest.get("ruleset_id")
        
        if ruleset_id:
            ruleset = self.db.rulesets.get_by_id(ruleset_id)
            if ruleset:
                sections.append(self._render_physics(ruleset))

        if game_session.authors_note:
            sections.append("# AUTHOR'S NOTE")
            sections.append(game_session.authors_note)

        return "\\n\\n".join(sections)

    def build_dynamic_context(
        self,
        game_session: GameSession,
        chat_history: List[Message],
    ) -> str:
        sections = []
        last_user_msg = ""
        for msg in reversed(chat_history):
            if msg.role == "user":
                last_user_msg = msg.content
                break

        # 1. State
        state_text = self.state_builder.build(game_session.id)
        if state_text:
            sections.append(f"# CURRENT STATE #\\n{state_text}")

        # 2. Active Procedure
        manifest = SetupManifest(self.db).get_manifest(game_session.id)
        ruleset_id = manifest.get("ruleset_id")
        current_mode = game_session.game_mode.lower() 
        
        if ruleset_id:
            ruleset = self.db.rulesets.get_by_id(ruleset_id)
            if ruleset:
                proc_text = self._render_procedures(ruleset, current_mode)
                if proc_text:
                    sections.append(f"# ACTIVE PROCEDURE: {current_mode.upper()}\\n{proc_text}")

        # 3. RAG Rules
        if ruleset_id and last_user_msg:
            relevant_rules = self.vs.search_rules(ruleset_id, last_user_msg, k=3)
            if relevant_rules:
                rule_block = "\\n".join([f"- {r['content']}" for r in relevant_rules])
                sections.append(f"# RELEVANT MECHANICS\\n{rule_block}")

        # 4. Spatial
        spatial_context = self._build_spatial_context(game_session.id)
        if spatial_context:
            sections.append(spatial_context)

        # 5. Narrative Memory
        active_npc_keys = self._get_active_npc_keys(game_session.id)
        session = Session.from_json(game_session.session_data)
        session.id = game_session.id
        memories = self.mem_retriever.get_relevant(
            session, chat_history, active_npc_keys=active_npc_keys
        )
        mem_text = self.mem_retriever.format_for_prompt(memories)
        if mem_text:
            sections.append(mem_text)

        return "\\n\\n".join(sections)

    def _render_physics(self, ruleset) -> str:
        p = ruleset.physics
        lines = ["# CORE PHYSICS"]
        lines.append(f"- **Dice**: {p.dice_notation}")
        lines.append(f"- **Mechanic**: {p.roll_mechanic}")
        lines.append(f"- **Success**: {p.success_condition}")
        lines.append(f"- **Crit/Fail**: {p.crit_rules}")
        return "\\n".join(lines)

    def _render_procedures(self, ruleset, mode: str) -> str:
        loops = ruleset.gameplay_procedures
        target_dict = {}
        
        if mode == "combat" or mode == "encounter": 
            target_dict = loops.encounter
        elif mode == "exploration": 
            target_dict = loops.exploration
        elif mode == "social": 
            target_dict = loops.social
        elif mode == "downtime": 
            target_dict = loops.downtime
        else:
            # Fallback to misc if mode is weird, or just return empty
            return ""
        
        if not target_dict:
            return ""
            
        lines = []
        for name, proc in target_dict.items():
            lines.append(f"**{name} ({proc.description})**")
            for step in proc.steps:
                lines.append(f"  {step}")
            lines.append("") # Spacer between procedures
            
        return "\\n".join(lines)

    def _build_spatial_context(self, session_id: int) -> str:
        try:
            scene = self.db.game_state.get_entity(session_id, "scene", "active_scene")
            if not scene: return ""
            lines = []
            loc_key = scene.get("location_key")
            if loc_key:
                location = self.db.game_state.get_entity(session_id, "location", loc_key)
                if location:
                    lines.append(f"# LOCATION: {location.get('name', 'Unknown')} #")
                    lines.append(location.get("description_visual", ""))
                    conns = location.get("connections", {})
                    if conns:
                        exits = [f"{d.upper()} -> {data.get('display_name')}" for d, data in conns.items()]
                        lines.append("Exits: " + ", ".join(exits))
            
            tmap = scene.get("tactical_map", {})
            positions = tmap.get("positions", {})
            if positions:
                lines.append("\\n# TACTICAL OVERVIEW #")
                player_pos = self._parse_coord(positions.get("player", "A1"))
                for key, coord_str in positions.items():
                    if key == "player": continue
                    name = key.split(":")[-1].title()
                    npc_pos = self._parse_coord(coord_str)
                    dist = math.dist(player_pos, npc_pos) * 5
                    
                    if dist <= 5: tag = "Melee Range"
                    elif dist <= 15: tag = "Near"
                    elif dist <= 30: tag = "Short Range"
                    else: tag = "Far"
                    lines.append(f"- {name}: {int(dist)}ft away [{tag}]")
            return "\\n".join(lines)
        except Exception:
            return ""

    def _parse_coord(self, coord: str) -> tuple[int, int]:
        if not coord or len(coord) < 2: return (0, 0)
        try:
            col = ord(coord[0].upper()) - 65
            row = int(coord[1:]) - 1
            return (col, row)
        except: return (0, 0)

    def _get_active_npc_keys(self, session_id: int) -> List[str]:
        try:
            scene = self.db.game_state.get_entity(session_id, "scene", "active_scene")
            if not scene: return []
            return [m.split(":", 1)[1] for m in scene.get("members", []) if m.startswith("character:") and "player" not in m]
        except: return []

    def get_truncated_history(self, session: Session, max_messages: int) -> List[Message]:
        history = session.get_history()
        return history[-max_messages:] if len(history) > max_messages else history
"""

# ==============================================================================
# 5. DIALOG UPDATE: Count properties correctly with new structure
# ==============================================================================
FILES[
    "app/gui/panels/prompt_dialog.py"
] = """\"\"\"Prompt Dialog with Optimized Counting.\"\"\"
import customtkinter as ctk
import logging
from typing import Optional
from app.gui.styles import Theme
from app.llm.llm_connector import LLMConnector

class PromptDialog(ctk.CTkToplevel):
    def __init__(self, parent, title="New Prompt", existing_prompt=None, llm_connector=None):
        super().__init__(parent)
        self.title(title)
        self.geometry("1024x720")
        self.result = None
        self.existing_prompt = existing_prompt
        self.llm_connector = llm_connector
        self._create_widgets()
        self._load_existing_data()
        self.transient(parent)
        self.grab_set()

    def _create_widgets(self):
        main = ctk.CTkScrollableFrame(self)
        main.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(main, text="Name:", font=Theme.fonts.subheading).pack(fill="x")
        self.name_entry = ctk.CTkEntry(main)
        self.name_entry.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(main, text="System Prompt:", font=Theme.fonts.subheading).pack(fill="x")
        self.content_textbox = ctk.CTkTextbox(main, height=200)
        self.content_textbox.pack(fill="both", expand=True, pady=(0, 15))

        ctk.CTkLabel(main, text="Rules Document:", font=Theme.fonts.subheading).pack(fill="x")
        self.rules_textbox = ctk.CTkTextbox(main, height=200)
        self.rules_textbox.pack(fill="both", expand=True, pady=(0, 15))

        gen_frame = ctk.CTkFrame(main, fg_color="transparent")
        gen_frame.pack(fill="x", pady=(0, 15))
        self.generate_btn = ctk.CTkButton(gen_frame, text="Generate Template", command=self._generate)
        self.generate_btn.pack(side="left")
        self.gen_status = ctk.CTkLabel(gen_frame, text="", text_color="gray")
        self.gen_status.pack(side="left", padx=10)

        ctk.CTkLabel(main, text="Template JSON:", font=Theme.fonts.subheading).pack(fill="x")
        self.template_textbox = ctk.CTkTextbox(main, height=200)
        self.template_textbox.pack(fill="both", expand=True, pady=(0, 15))

        btns = ctk.CTkFrame(main, fg_color="transparent")
        btns.pack(fill="x")
        ctk.CTkButton(btns, text="Cancel", command=self.destroy).pack(side="left")
        ctk.CTkButton(btns, text="Save", command=self._save).pack(side="right")

    def _generate(self):
        import threading
        rules = self.rules_textbox.get("1.0", "end-1c").strip()
        if not rules: return
        self.gen_status.configure(text="Generating...")
        self.generate_btn.configure(state="disabled")
        threading.Thread(target=self._gen_thread, args=(rules,), daemon=True).start()

    def _gen_thread(self, rules):
        try:
            from app.setup.template_generation_service import TemplateGenerationService
            gen = TemplateGenerationService(self.llm_connector, rules, lambda m: self.after(0, self._upd_status, m))
            rs, st = gen.generate_template()
            self.after(0, self._on_gen, {"ruleset": rs.model_dump(), "stat_template": st.model_dump()}, None)
        except Exception as e:
            self.after(0, self._on_gen, None, str(e))

    def _upd_status(self, msg):
        self.gen_status.configure(text=msg)

    def _on_gen(self, data, err):
        self.generate_btn.configure(state="normal")
        if err:
            self.gen_status.configure(text=f"Error: {err}", text_color="red")
            return
        
        import json
        self.template_textbox.delete("1.0", "end")
        self.template_textbox.insert("1.0", json.dumps(data, indent=2))
        
        # Count Props (Dict based + New Structure)
        count = 0
        rs = data.get("ruleset", {})
        count += len(rs.get("rules", {})) # Renamed from mechanics
        
        # Procedures
        loops = rs.get("gameplay_procedures", {})
        count += len(loops.get("encounter", {}))
        count += len(loops.get("exploration", {}))
        count += len(loops.get("social", {}))
        count += len(loops.get("downtime", {}))
        count += len(loops.get("misc", {}))
        
        st = data.get("stat_template", {})
        count += len(st.get("fundamental_stats", {}))
        count += len(st.get("derived_stats", {}))
        count += len(st.get("vital_resources", {}))
        count += len(st.get("consumable_resources", {}))
        count += len(st.get("skills", {}))
        count += len(st.get("features", {}))
        count += len(st.get("equipment", {}).get("slots", {}))
        
        self.gen_status.configure(text=f"Generated {count} properties", text_color="green")

    def _save(self):
        name = self.name_entry.get().strip()
        content = self.content_textbox.get("1.0", "end-1c").strip()
        rules = self.rules_textbox.get("1.0", "end-1c").strip()
        tpl = self.template_textbox.get("1.0", "end-1c").strip()
        if name and content:
            self.result = (name, content, rules, tpl)
            self.grab_release()
            self.destroy()

    def _load_existing_data(self):
        if self.existing_prompt:
            self.name_entry.insert(0, self.existing_prompt.name)
            self.content_textbox.insert("1.0", self.existing_prompt.content)
            self.rules_textbox.insert("1.0", self.existing_prompt.rules_document or "")
            self.template_textbox.insert("1.0", self.existing_prompt.template_manifest or "{}")

    def get_result(self): return self.result
"""


def apply_update():
    print("🚀 Applying Multi-Procedure & Field Rename Patch...")
    for filepath, content in FILES.items():
        filepath = filepath.replace("/", os.sep)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        print(f"📝 Updating {filepath}...")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    print("✅ Done. You now have dictionary-based procedures!")


if __name__ == "__main__":
    apply_update()
