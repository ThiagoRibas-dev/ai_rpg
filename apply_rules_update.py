import os

FILES = {}

# ==============================================================================
# 1. MODELS: STATBLOCK (Refined IdentityDef)
# ==============================================================================
FILES["app/models/stat_block.py"] = """\"\"\"
Models for the Refined StatBlock Template.
Implements granular categorization for Identity, Equipment, and Resources.
\"\"\"

from typing import List, Optional, Literal, Union
from pydantic import BaseModel, Field


class IdentityDef(BaseModel):
    \"\"\"
    Defines a category of identity.
    e.g. "Species" (Race), "Profession" (Class), "Background".
    \"\"\"
    category_name: str = Field(..., description="e.g. 'Race', 'Playbook', 'Background'")
    description: Optional[str] = None
    allow_multiple: bool = Field(False, description="Can you have two of these? (e.g. Multiclassing)")
    # TWEAK: Distinguish between selecting from a list (Class) vs writing free text (Beliefs/Instincts)
    value_type: Literal["selection", "text"] = Field("selection", description="Is this a specific option or free text?")


class FundamentalStatDef(BaseModel):
    \"\"\"
    BASE ATTRIBUTES. The raw inputs for the system's math.
    e.g. Strength, Agility, Logic.
    \"\"\"
    name: str
    abbr: Optional[str] = None
    description: Optional[str] = None
    data_type: Literal["integer", "die_code", "dots", "float"] = "integer"
    default: Union[int, str, float] = 10


class DerivedStatDef(BaseModel):
    \"\"\"
    CALCULATED VALUES. Read-only outputs.
    e.g. AC, Initiative, Save DC.
    \"\"\"
    name: str
    formula: str = Field(..., description="Python math string.")


class VitalResourceDef(BaseModel):
    \"\"\"
    LIFE METERS.
    If this runs out (or fills up), the character dies, goes mad, or is taken out.
    e.g. HP, Sanity, Stress.
    \"\"\"
    name: str
    type: Literal["depleting", "accumulating"] = "depleting"
    min_value: int = 0
    max_formula: Optional[str] = Field(None, description="Formula for max value.")
    on_zero: Optional[str] = Field(None, description="Effect at 0 (e.g. 'Death').")
    on_max: Optional[str] = Field(None, description="Effect at max (e.g. 'Panic').")


class ConsumableResourceDef(BaseModel):
    \"\"\"
    FUEL / EXPANDABLES.
    Spent to use abilities. Reloaded via rest/actions.
    e.g. Spell Slots, Ki, Ammo, Power Points.
    \"\"\"
    name: str
    reset_trigger: str = Field("Rest", description="When does this refill?")
    max_formula: Optional[str] = Field(None, description="Formula for max capacity.")


class SkillDef(BaseModel):
    \"\"\"
    LEARNED PROFICIENCIES.
    \"\"\"
    name: str
    linked_stat: Optional[str] = Field(None, description="Associated Fundamental Stat.")
    can_be_untrained: bool = True


class FeatureContainerDef(BaseModel):
    \"\"\"
    Buckets for special abilities.
    e.g. "Feats", "Class Features", "Spells Known".
    \"\"\"
    name: str
    description: Optional[str] = None


class BodySlotDef(BaseModel):
    \"\"\"
    A specific location on the body to equip items.
    e.g. 'Main Hand', 'Off Hand', 'Ring 1', 'Ring 2'.
    \"\"\"
    name: str
    description: Optional[str] = None
    accepted_item_types: List[str] = Field(default_factory=list, description="e.g. ['Ring'], ['Weapon', 'Shield']")


class EquipmentConfig(BaseModel):
    \"\"\"
    Inventory definition.
    \"\"\"
    capacity_stat: Optional[str] = Field(None, description="CalculatedStat defining carry limit.")
    slots: List[BodySlotDef] = Field(default_factory=list)


class StatBlockTemplate(BaseModel):
    \"\"\"
    The blueprint for an Entity.
    \"\"\"
    template_name: str
    
    identity_categories: List[IdentityDef] = Field(default_factory=list)
    fundamental_stats: List[FundamentalStatDef] = Field(default_factory=list)
    derived_stats: List[DerivedStatDef] = Field(default_factory=list)
    
    vital_resources: List[VitalResourceDef] = Field(default_factory=list)
    consumable_resources: List[ConsumableResourceDef] = Field(default_factory=list)
    
    skills: List[SkillDef] = Field(default_factory=list)
    features: List[FeatureContainerDef] = Field(default_factory=list)
    
    equipment: EquipmentConfig = Field(default_factory=EquipmentConfig)
"""

# ==============================================================================
# 2. MODELS: RULESET (Renamed General -> General Procedures)
# ==============================================================================
FILES["app/models/ruleset.py"] = """\"\"\"
Models for the Game System Rules.
Organized by Domain (Physics, Economy, Scripts).
\"\"\"

from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class RuleEntry(BaseModel):
    \"\"\"Atomic rule for RAG.\"\"\"
    name: str
    text: str
    tags: List[str] = Field(default_factory=list)


class PhysicsConfig(BaseModel):
    \"\"\"The Resolution Engine.\"\"\"
    dice_notation: str = Field(..., description="e.g. '1d20', '3d6'")
    roll_mechanic: str = Field(..., description="e.g. 'Roll + Mod vs DC', 'Roll under Skill'")
    success_condition: str = Field(..., description="e.g. 'Total >= Target'")
    crit_rules: str = Field("Nat 20 / Nat 1", description="Critical success/failure rules.")


class ProcedureDef(BaseModel):
    \"\"\"A specific game loop.\"\"\"
    name: str
    description: str
    steps: List[str] = Field(default_factory=list)


class GameLoopConfig(BaseModel):
    \"\"\"Procedures grouped by mode.\"\"\"
    combat: Optional[ProcedureDef] = None
    exploration: Optional[ProcedureDef] = None
    social: Optional[ProcedureDef] = None
    downtime: Optional[ProcedureDef] = None
    # TWEAK: Renamed for clarity
    general_procedures: List[ProcedureDef] = Field(default_factory=list)


class Ruleset(BaseModel):
    \"\"\"Root Configuration.\"\"\"
    meta: Dict[str, str] = Field(default_factory=lambda: {"name": "Untitled", "genre": "Generic"})
    
    physics: PhysicsConfig
    gameplay_loops: GameLoopConfig = Field(default_factory=GameLoopConfig)
    
    # Static Library (The Compendium)
    mechanics: List[RuleEntry] = Field(default_factory=list)
"""

# ==============================================================================
# 3. TOOLS: SCHEMAS (Inventory target_slot)
# ==============================================================================
FILES["app/tools/schemas.py"] = """from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field

# A reusable JSON type
JSONValue = Union[str, int, float, bool, dict, List]

# --- SUPER TOOLS (ReAct Engine) ---

class EntityUpdate(BaseModel):
    \"\"\"
    Update an entity's state (Character, NPC, Object).
    - adjustments: Relative math (e.g. {'hp': -5, 'gold': +10})
    - updates: Absolute sets (e.g. {'status': 'Prone', 'disposition': 'Hostile'})
    - inventory: Manage items (e.g. {'add': {'name': 'Key', 'qty': 1}})
    \"\"\"
    name: Literal["entity.update"] = "entity.update"
    target_key: str = Field(..., description="Entity ID (e.g., 'player', 'goblin_1').")
    adjustments: Optional[Dict[str, int]] = Field(None, description="Math changes. e.g. {'hp': -5}.")
    updates: Optional[Dict[str, Any]] = Field(None, description="Absolute sets. e.g. {'status': 'Prone'}.")
    inventory: Optional[Dict[str, Any]] = Field(None, description="Inventory changes. e.g. {'add': {'name': 'Sword'}}.")

class GameRoll(BaseModel):
    \"\"\"
    Roll dice for a check, attack, or save.
    \"\"\"
    name: Literal["game.roll"] = "game.roll"
    formula: str = Field(..., description="Dice string (e.g., '1d20+5').")
    reason: str = Field(..., description="Context for the roll (e.g., 'Attack vs Goblin AC').")

class WorldTravel(BaseModel):
    \"\"\"
    Move the party to a different location.
    \"\"\"
    name: Literal["world.travel"] = "world.travel"
    destination: str = Field(..., description="Target Location Key (e.g., 'tavern_common_room').")

class GameLog(BaseModel):
    \"\"\"
    Record a memory, quest update, or important fact.
    \"\"\"
    name: Literal["game.log"] = "game.log"
    content: str = Field(..., description="The fact or event to remember.")
    category: Literal["event", "fact", "quest"] = Field("event", description="Type of log.")
    tags: Optional[List[str]] = Field(None, description="Search tags.")

class TimeAdvance(BaseModel):
    \"\"\"
    Advance fictional game time (triggers world simulation).
    \"\"\"
    name: Literal["time.advance"] = "time.advance"
    description: str = Field(..., description="Narrative description (e.g. 'You sleep for 8 hours').")
    new_time: str = Field(..., description="The new time string.")

# --- WIZARD / SETUP TOOLS (Keep for SetupWizard) ---

class NpcSpawn(BaseModel):
    name: Literal["npc.spawn"] = "npc.spawn"
    key: str = Field(..., description="Unique ID.")
    name_display: str = Field(..., description="Name shown to player.")
    visual_description: str = Field(..., description="Physical appearance.")
    stat_template: str = Field(..., description="Template name (e.g. 'Commoner').")
    initial_disposition: Literal["hostile", "neutral", "friendly"] = Field("neutral")
    location_key: Optional[str] = Field(None)

class LocationCreate(BaseModel):
    name: Literal["location.create"] = "location.create"
    key: str = Field(..., description="Unique ID.")
    name_display: str = Field(..., description="Display name.")
    description_visual: str = Field(..., description="Visuals.")
    description_sensory: str = Field(..., description="Smell, sound.")
    type: str = Field(..., description="Environment type.")
    neighbors: List[Dict[str, str]] = Field(default_factory=list)

class MemoryUpsert(BaseModel):
    \"\"\"Legacy wrapper for Wizard lore generation.\"\"\"
    name: Literal["memory.upsert"] = "memory.upsert"
    kind: str = Field(...)
    content: str = Field(...)
    priority: int = 3
    tags: Optional[List[str]] = None

# --- UTILS ---

class MathEval(BaseModel):
    name: Literal["math.eval"] = "math.eval"
    expression: str = Field(..., description="Math expression.")

class StateQuery(BaseModel):
    name: Literal["state.query"] = "state.query"
    entity_type: str = Field(...)
    key: str = Field(...)
    json_path: str = Field(...)

class InventoryAddItem(BaseModel):
    \"\"\"Directly add items to specific slots.\"\"\"
    name: Literal["inventory.add_item"] = "inventory.add_item"
    owner_key: str = Field(...)
    item_name: str = Field(...)
    quantity: int = 1
    description: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    # TWEAK: Optional slot override
    target_slot: Optional[str] = Field(None, description="Force item into this slot (e.g. 'Load 1'). Overrides rules.")

class CharacterUpdate(BaseModel):
    \"\"\"Kept for Wizard compatibility.\"\"\"
    name: Literal["character.update"] = "character.update"
    character_key: str = Field(...)
    updates: List[Any] = Field(...)

class Deliberate(BaseModel):
    name: Literal["deliberate"] = "deliberate"
"""

# ==============================================================================
# 4. TOOLS: INVENTORY HANDLER (Logic update)
# ==============================================================================
FILES["app/tools/builtin/inventory_add_item.py"] = """import time
import logging
from typing import Optional, Dict, Any
from app.tools.builtin._state_storage import get_entity, set_entity

logger = logging.getLogger(__name__)

def handler(
    owner_key: str,
    item_name: str,
    quantity: int = 1,
    description: Optional[str] = None,
    properties: Optional[Dict[str, Any]] = None,
    target_slot: Optional[str] = None,
    **context: Any,
) -> dict:
    \"\"\"
    Handler for inventory.add_item. 
    Adds item to an appropriate Slot in the character's StatBlock.
    If target_slot is provided, it forces creation/usage of that slot (Narrative Game style).
    \"\"\"
    session_id = context["session_id"]
    db = context["db_manager"]

    # 1. Load Owner (Character)
    owner = get_entity(session_id, db, "character", owner_key)
    if not owner:
        raise ValueError(f"Owner '{owner_key}' not found.")

    # 2. Determine Slot
    target_slot_name = "Inventory" # Default fallback

    # TWEAK: Check for manual override first
    if target_slot:
        target_slot_name = target_slot
        logger.info(f"Adding item to requested slot: {target_slot_name}")
    else:
        # Template-based logic
        template_id = owner.get("template_id")
        stat_template = None
        if template_id:
            stat_template = db.stat_templates.get_by_id(template_id)
        
        if stat_template:
            # Find the first slot that accepts "item" or has "inventory" in name
            for slot_def in stat_template.slots:
                if "item" in slot_def.accepts_tags or "Inventory" in slot_def.name:
                    target_slot_name = slot_def.name
                    break
    
    # 3. Access Slot Data
    slots_data = owner.setdefault("slots", {})
    # This line effectively creates dynamic slots if they don't exist
    target_slot_items = slots_data.setdefault(target_slot_name, [])
    
    # 4. Logic: Increment or Add
    action = "added"
    found = False
    
    for item in target_slot_items:
        if item.get("name") == item_name:
            item["quantity"] = item.get("quantity", 1) + quantity
            found = True
            action = "incremented"
            break
    
    if not found:
        new_item = {
            "id": f"item_{int(time.time())}",
            "name": item_name,
            "quantity": quantity,
            "description": description or "",
            "properties": properties or {}
        }
        target_slot_items.append(new_item)
    
    # 5. Capacity Check
    # We only check capacity if we found a template definition AND we aren't overriding
    if not target_slot:
        template_id = owner.get("template_id")
        stat_template = db.stat_templates.get_by_id(template_id) if template_id else None
        
        if stat_template:
            slot_def = next((s for s in stat_template.slots if s.name == target_slot_name), None)
            if slot_def and slot_def.fixed_capacity:
                total_count = sum(i.get("quantity", 1) for i in target_slot_items)
                if total_count > slot_def.fixed_capacity:
                     if slot_def.overflow_behavior == "prevent":
                         raise ValueError(f"Slot '{target_slot_name}' is full (Capacity: {slot_def.fixed_capacity}).")
    
    # 6. Save
    set_entity(session_id, db, "character", owner_key, owner)

    return {
        "success": True, 
        "action": action, 
        "item_name": item_name,
        "slot": target_slot_name
    }
"""

# ==============================================================================
# 5. SETUP: GENERATION SERVICE (Update general -> general_procedures)
# ==============================================================================
FILES["app/setup/template_generation_service.py"] = """import logging
from typing import Any, List, Callable, Optional, Type, TypeVar, Tuple
from pydantic import BaseModel, create_model, Field

from app.llm.llm_connector import LLMConnector
from app.models.message import Message
from app.models.ruleset import Ruleset, PhysicsConfig, GameLoopConfig, ProcedureDef, RuleEntry
from app.models.stat_block import (
    StatBlockTemplate, IdentityDef, FundamentalStatDef, DerivedStatDef, 
    VitalResourceDef, ConsumableResourceDef, SkillDef, FeatureContainerDef, EquipmentConfig
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
    \"\"\"
    Generates game templates using the Refined Ontology.
    \"\"\"

    def __init__(self, llm_connector: LLMConnector, rules_text: str, status_callback: Optional[Callable[[str], None]] = None):
        self.llm = llm_connector
        self.rules_text = rules_text
        self.status_callback = status_callback
        self.base_system_prompt = TEMPLATE_GENERATION_SYSTEM_PROMPT

    def _update_status(self, message: str):
        if self.status_callback:
            self.status_callback(message)
        logger.info(f"[TemplateGeneration] {message}")

    def _get_sys_prompt(self, game_name: str = "Unknown RPG"):
        return f"{self.base_system_prompt.format(game_name=game_name)}\\n\\n# GAME RULES TEXT\\n{self.rules_text}"

    def generate_template(self) -> Tuple[Ruleset, StatBlockTemplate]:
        
        # --- PHASE 1: RULES KERNEL ---
        self._update_status("Identifying Game Identity...")
        
        temp_sys_prompt = f"{self.base_system_prompt.format(game_name='Unknown')}\\n\\n# RULES START\\n{self.rules_text[:15000]}"
        
        class RulesetMeta(BaseModel):
            name: str
            genre: str
            description: str

        meta_res = self.llm.get_structured_response(
            system_prompt=temp_sys_prompt,
            chat_history=[Message(role="user", content=GENERATE_META_INSTRUCTION)],
            output_schema=RulesetMeta
        )
        
        meta_data = {
            "name": meta_res.name if meta_res else "Untitled System",
            "genre": meta_res.genre if meta_res else "Generic",
            "description": meta_res.description if meta_res else ""
        }
        game_name = meta_data["name"]
        self._update_status(f"Analyzed: {game_name}")
        sys_prompt = self._get_sys_prompt(game_name)

        # Physics
        self._update_status("Defining Physics...")
        phys_res = self.llm.get_structured_response(
            system_prompt=sys_prompt,
            chat_history=[Message(role="user", content=GENERATE_PHYSICS_INSTRUCTION)],
            output_schema=PhysicsConfig
        )

        # --- PHASE 2: STATBLOCK ---
        self._update_status("Analyzing Stats...")
        stat_analysis_gen = self.llm.get_streaming_response(sys_prompt, [Message(role="user", content=ANALYZE_STATBLOCK_INSTRUCTION)])
        stat_analysis = "".join(stat_analysis_gen)
        context = f"*** STAT ANALYSIS ***\\n{stat_analysis}\\n\\n"

        # Identity
        self._update_status("Defining Identity...")
        IdList = create_model("IdList", items=(List[IdentityDef], Field(default_factory=list)), __base__=BaseModel)
        id_res = self.llm.get_structured_response(sys_prompt, [Message(role="user", content=f"{context}{GENERATE_IDENTITY_INSTRUCTION}")], IdList)

        # Fundamental Stats
        self._update_status("Defining Fundamental Stats...")
        FundList = create_model("FundList", items=(List[FundamentalStatDef], Field(default_factory=list)), __base__=BaseModel)
        fund_res = self.llm.get_structured_response(sys_prompt, [Message(role="user", content=f"{context}{GENERATE_FUNDAMENTAL_INSTRUCTION}")], FundList)
        
        # Variable Injection
        fund_names = [c.name for c in (fund_res.items if fund_res else [])]
        var_list = ", ".join(fund_names) + ", " + ", ".join([f"{n}_Mod" for n in fund_names])
        self._update_status(f"Variables: {var_list[:50]}...")

        # Derived
        self._update_status("Defining Derived Stats...")
        DerList = create_model("DerList", items=(List[DerivedStatDef], Field(default_factory=list)), __base__=BaseModel)
        prompt_der = GENERATE_DERIVED_INSTRUCTION.format(variable_list=var_list)
        der_res = self.llm.get_structured_response(sys_prompt, [Message(role="user", content=f"{context}{prompt_der}")], DerList)
        
        if der_res and der_res.items:
            var_list += ", " + ", ".join([d.name for d in der_res.items])

        # Vitals
        self._update_status("Defining Vitals...")
        VitList = create_model("VitList", items=(List[VitalResourceDef], Field(default_factory=list)), __base__=BaseModel)
        prompt_vit = GENERATE_VITALS_INSTRUCTION.format(variable_list=var_list)
        vit_res = self.llm.get_structured_response(sys_prompt, [Message(role="user", content=f"{context}{prompt_vit}")], VitList)

        # Consumables
        self._update_status("Defining Consumables...")
        ConList = create_model("ConList", items=(List[ConsumableResourceDef], Field(default_factory=list)), __base__=BaseModel)
        con_res = self.llm.get_structured_response(sys_prompt, [Message(role="user", content=f"{context}{GENERATE_CONSUMABLES_INSTRUCTION}")], ConList)

        # Skills
        self._update_status("Defining Skills...")
        SkillList = create_model("SkillList", items=(List[SkillDef], Field(default_factory=list)), __base__=BaseModel)
        skill_res = self.llm.get_structured_response(sys_prompt, [Message(role="user", content=f"{context}{GENERATE_SKILLS_INSTRUCTION}")], SkillList)

        # Features
        self._update_status("Defining Feature Buckets...")
        FeatList = create_model("FeatList", items=(List[FeatureContainerDef], Field(default_factory=list)), __base__=BaseModel)
        feat_res = self.llm.get_structured_response(sys_prompt, [Message(role="user", content=f"{context}{GENERATE_FEATURES_INSTRUCTION}")], FeatList)

        # Equipment
        self._update_status("Defining Equipment...")
        eq_res = self.llm.get_structured_response(sys_prompt, [Message(role="user", content=f"{context}{GENERATE_EQUIPMENT_INSTRUCTION}")], EquipmentConfig)

        stat_template = StatBlockTemplate(
            template_name=game_name + " Character",
            identity_categories=id_res.items if id_res else [],
            fundamental_stats=fund_res.items if fund_res else [],
            derived_stats=der_res.items if der_res else [],
            vital_resources=vit_res.items if vit_res else [],
            consumable_resources=con_res.items if con_res else [],
            skills=skill_res.items if skill_res else [],
            features=feat_res.items if feat_res else [],
            equipment=eq_res if eq_res else EquipmentConfig()
        )

        # --- PHASE 3: MODES ---
        self._update_status("Identifying Game Modes...")
        class GameModes(BaseModel):
            names: List[str]
        modes_res = self.llm.get_structured_response(sys_prompt, [Message(role="user", content=IDENTIFY_MODES_INSTRUCTION)], GameModes)
        
        loops = GameLoopConfig()
        detected_modes = modes_res.names[:5] if modes_res else []
        
        for mode in detected_modes:
            self._update_status(f"Extracting Procedure: {mode}...")
            try:
                prompt = EXTRACT_PROCEDURE_INSTRUCTION.format(mode_name=mode)
                proc_def = self.llm.get_structured_response(sys_prompt, [Message(role="user", content=prompt)], ProcedureDef)
                
                # Map to schema fields if match
                m_lower = mode.lower()
                if "combat" in m_lower: loops.combat = proc_def
                elif "exploration" in m_lower: loops.exploration = proc_def
                elif "social" in m_lower: loops.social = proc_def
                elif "downtime" in m_lower: loops.downtime = proc_def
                # TWEAK: Use renamed field
                else: loops.general_procedures.append(proc_def)
                
            except Exception:
                pass

        # Mechanics (RAG)
        self._update_status("Extracting Mechanics...")
        class MechanicsOutput(BaseModel):
            rules: List[RuleEntry]
        mech_res = self.llm.get_structured_response(
            system_prompt=sys_prompt,
            chat_history=[Message(role="user", content=GENERATE_MECHANICS_INSTRUCTION)],
            output_schema=MechanicsOutput
        )

        ruleset = Ruleset(
            meta=meta_data,
            physics=phys_res,
            gameplay_loops=loops,
            mechanics=mech_res.rules if mech_res else []
        )

        return ruleset, stat_template
"""

def apply_tweaks():
    print("Ã°Å¸â€º ï¸   Applying Tweaks (Flexible Inventory, General Procedures, Identity Values)...")
    for filepath, content in FILES.items():
        filepath = filepath.replace("/", os.sep)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        print(f"Ã°Å¸â€œ  Updating {filepath}...")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    print("Ã¢Å“â€¦ Done.")

if __name__ == "__main__":
    apply_tweaks()