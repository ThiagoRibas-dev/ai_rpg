import os

FILES = {}

# ==============================================================================
# 1. MODELS: FLATTENED LAYOUT SCHEMA
# ==============================================================================
FILES["app/models/stat_block.py"] = """\"\"\"
Models for the Generic Functional StatBlock.
Layout is now flattened: Stats directly declare their Panel and Group.
\"\"\"

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field

# --- UI Definitions ---

class WidgetType(str):
    TEXT_LINE = "text_line"
    TEXT_AREA = "text_area"
    NUMBER = "number"
    BONUS = "bonus"
    DIE = "die"
    DOTS = "dots"
    CHECKBOX = "checkbox"
    BAR = "bar"
    CLOCK = "clock"
    FRACTION = "fraction"
    CHECK_GRID = "check_grid"

class PanelType(str):
    HEADER = "header"       # Top bar (Name, Class)
    SIDEBAR = "sidebar"     # Left col (Attributes, Saves)
    MAIN = "main"           # Center (Combat, Actions)
    EQUIPMENT = "equipment" # Inventory
    SPELLS = "spells"       # Magic
    NOTES = "notes"         # Bio

# --- Data Primitives ---

class StatValue(BaseModel):
    id: str = Field(..., description="Unique key (e.g. 'str').")
    label: str = Field(..., description="Display name.")
    data_type: Literal["string", "integer", "boolean", "formula"] = "integer"
    default: Any = 0
    calculation: Optional[str] = None
    
    # Direct Layout Assignment
    widget: str = "number"
    panel: str = Field("main", description="Target Panel (header, sidebar, main, etc).")
    group: str = Field("General", description="Section header within the panel (e.g. 'Attributes').")

class StatGauge(BaseModel):
    id: str = Field(..., description="Unique key (e.g. 'hp').")
    label: str = Field(..., description="Display name.")
    min_val: int = 0
    max_formula: str = "10"
    reset_on_rest: bool = True
    
    widget: str = "bar"
    panel: str = Field("main", description="Target Panel.")
    group: str = Field("Vitals", description="Section header.")

class CollectionItemField(BaseModel):
    key: str
    label: str
    data_type: Literal["string", "integer", "boolean"] = "string"
    widget: str = "text_line"

class StatCollection(BaseModel):
    id: str = Field(..., description="Unique key (e.g. 'inventory').")
    label: str = Field(..., description="Display name.")
    item_schema: List[CollectionItemField] = Field(default_factory=list)
    
    panel: str = Field("equipment", description="Target Panel.")
    group: str = Field("Items", description="Section header.")

# --- Root Template ---

class StatBlockTemplate(BaseModel):
    template_name: str
    values: Dict[str, StatValue] = Field(default_factory=dict)
    gauges: Dict[str, StatGauge] = Field(default_factory=dict)
    collections: Dict[str, StatCollection] = Field(default_factory=dict)
    # layout_groups is removed. Logic is distributed.
"""

# ==============================================================================
# 2. PROMPTS: STRICTER PROCEDURES & SIMPLE LAYOUT
# ==============================================================================
FILES["app/prompts/templates.py"] = """\"\"\"
Templates for LLM prompts.
Updated for Flattened Layout and Strict Procedure Extraction.
\"\"\"

# --- GAMEPLAY ---
GAME_MASTER_SYSTEM_PROMPT = \"\"\"
You are an expert Game Master (GM).
Your goal is to provide a vivid, immersive experience while adhering to the extracted rules.
\"\"\"

# --- TEMPLATE GENERATION ---

TEMPLATE_GENERATION_SYSTEM_PROMPT = \"\"\"
You are a **Tabletop RPG Database Architect**.
Your goal is to design a **BLANK Character Sheet Template** and extract **Game Rules**.

### CRITICAL INSTRUCTIONS
1. **Design the Form, Don't Fill It:** Define the schema (Columns), not the data (Rows).
2. **Generic Defaults:** Use 0, 10, or "" as defaults. Never use specific character data.
3. **No Meta-Commentary:** When extracting rules or procedures, output ONLY the content. Do not say "Here is the procedure" or "I found this text".
\"\"\"

# Phase 1: Core Stats
GENERATE_CORE_STATS_INSTRUCTION = \"\"\"
Identify the **Fixed Global Stats** (Values & Gauges).

**DISTINCTIONS:**
*   **StatValue**: Static properties (Str, Dex, Level, AC).
*   **StatGauge**: Fluctuating resources (HP, Mana, Ammo).

**CONSTRAINTS:**
*   Mutually Exclusive: A stat cannot be both Value and Gauge.
*   Formulas: Use Python syntax (`10 + dex`) for derived stats. Do not write the result (`14`).

Output a JSON with `values` and `gauges`.
\"\"\"

# Phase 2: Containers
GENERATE_CONTAINERS_INSTRUCTION = \"\"\"
Identify the **Dynamic Lists** (Collections).
Define the **Table Schema** (Columns) for items in these lists.

Examples:
- Skills (Name, Rank)
- Inventory (Name, Weight)
- Spells (Name, Cost, Effect)

Output a JSON with `collections`.
\"\"\"

# Phase 3: Layout (Flattened)
ORGANIZE_LAYOUT_INSTRUCTION = \"\"\"
Assign every defined Stat (Value, Gauge, Collection) to a **Panel** and a **Group**.

**PANELS (Strict Assignment):**
*   `header`: Vital info (HP, Name, Level, Class, XP).
*   `sidebar`: Core Stats (Attributes, Saves, Passive Defenses).
*   `main`: Combat actions, Attacks, Initiative, Speed.
*   `equipment`: Inventory, Money, Encumbrance.
*   `skills`: Skill lists.
*   `spells`: Magic/Powers.
*   `notes`: Bio, Background.

**INSTRUCTION:**
Update the objects to set their `panel` field.
Use the `group` field to label the section within that panel (e.g. Panel: 'sidebar', Group: 'Attributes').
Do NOT dump everything in 'main'.
\"\"\"

# Phase 4: Procedures (Strict)
IDENTIFY_MODES_INSTRUCTION = \"\"\"
Identify the distinct **Game Modes** (Loops).
Return ONLY a JSON list of strings.
Example: `["Combat", "Exploration", "Social"]`
\"\"\"

EXTRACT_PROCEDURE_INSTRUCTION = \"\"\"
Extract the step-by-step **Procedure** for **{mode_name}**.

**STRICT FORMATTING:**
*   `description`: A concise summary of what this mode resolves.
*   `steps`: A list of strings. Each string is one step.
*   **NO CHAT:** Do not write "The user is asking..." or "I will extract...". Just output the data.
\"\"\"

# Phase 5: Mechanics
GENERATE_MECHANICS_INSTRUCTION = \"\"\"
Extract specific **Game Rules** (Conditions, Actions, Magic Rules) for the Reference Index.
Key: Rule Name. Value: Rule Text + Tags.
\"\"\"

# --- WORLD GEN ---
CHARACTER_EXTRACTION_PROMPT = \"\"\"
Extract character data into the schema.
Context: {template}
Input: "{description}"
\"\"\"

WORLD_EXTRACTION_PROMPT = \"\"\"
Extract world details.
Input: "{description}"
\"\"\"

OPENING_CRAWL_PROMPT = \"\"\"
Write a 2nd-person opening scene.
Genre: {genre}
Protagonist: {name}
Location: {location}
\"\"\"

JIT_SIMULATION_TEMPLATE = \"\"\"
Simulate NPC actions.
NPC: {npc_name}
Time: {last_updated_time} -> {current_time}
\"\"\"
"""

# ==============================================================================
# 3. SERVICE: UPDATING LOGIC FOR FLATTENED LAYOUT
# ==============================================================================
FILES["app/setup/template_generation_service.py"] = """import logging
from typing import List, Callable, Optional, Tuple, Dict
from pydantic import BaseModel, Field

from app.llm.llm_connector import LLMConnector
from app.models.message import Message
from app.models.ruleset import Ruleset, PhysicsConfig, GameLoopConfig, ProcedureDef, RuleEntry
from app.models.stat_block import (
    StatBlockTemplate, StatValue, StatGauge, StatCollection
)
from app.prompts.templates import (
    TEMPLATE_GENERATION_SYSTEM_PROMPT,
    GENERATE_CORE_STATS_INSTRUCTION,
    GENERATE_CONTAINERS_INSTRUCTION,
    ORGANIZE_LAYOUT_INSTRUCTION,
    IDENTIFY_MODES_INSTRUCTION,
    EXTRACT_PROCEDURE_INSTRUCTION,
    GENERATE_MECHANICS_INSTRUCTION
)

logger = logging.getLogger(__name__)

class TemplateGenerationService:
    \"\"\"
    Generates templates using the 5-step process with Flattened Layout.
    \"\"\"

    def __init__(self, llm_connector: LLMConnector, rules_text: str, status_callback: Optional[Callable[[str], None]] = None):
        self.llm = llm_connector
        self.rules_text = rules_text
        self.status_callback = status_callback
        self.static_system_prompt = f"{TEMPLATE_GENERATION_SYSTEM_PROMPT}\\n\\n# RULES REFERENCE\\n{self.rules_text}"

    def _update_status(self, message: str):
        if self.status_callback: self.status_callback(message)
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
            [Message(role="user", content="Extract Game Name, Genre, and Core Dice Mechanics.")],
            QuickMeta
        )
        
        ruleset = Ruleset(
            meta={"name": meta_res.name, "genre": meta_res.genre},
            physics=PhysicsConfig(
                dice_notation=meta_res.dice_notation,
                roll_mechanic=meta_res.roll_mechanic,
                success_condition="See Rules",
                crit_rules="See Rules"
            )
        )

        # --- STEP 1: CORE STATS ---
        self._update_status("Phase 1: Defining Core Stats...")
        class CoreStatsDef(BaseModel):
            values: List[StatValue]
            gauges: List[StatGauge]

        core_res = self.llm.get_structured_response(
            self.static_system_prompt,
            [Message(role="user", content=GENERATE_CORE_STATS_INSTRUCTION)],
            CoreStatsDef
        )
        
        # --- STEP 2: CONTAINERS ---
        self._update_status("Phase 2: Defining Containers...")
        stats_summary = f"Defined Values: {[v.id for v in core_res.values]}\\nDefined Gauges: {[g.id for g in core_res.gauges]}"
        
        class ContainerDef(BaseModel):
            collections: List[StatCollection]

        container_res = self.llm.get_structured_response(
            self.static_system_prompt,
            [
                Message(role="user", content=GENERATE_CORE_STATS_INSTRUCTION),
                Message(role="assistant", content=f"I have defined the core stats.\\n{stats_summary}"),
                Message(role="user", content=GENERATE_CONTAINERS_INSTRUCTION)
            ],
            ContainerDef
        )

        # --- STEP 3: LAYOUT (ASSIGNMENT) ---
        self._update_status("Phase 3: Assigning Panels...")
        
        # We ask the LLM to return the SAME lists, but with 'panel' and 'group' fields populated.
        # This acts as a "Refinement" pass.
        class LayoutAssignment(BaseModel):
            values: List[StatValue]
            gauges: List[StatGauge]
            collections: List[StatCollection]

        collections_summary = f"Defined Collections: {[c.id for c in container_res.collections]}"
        
        history_layout = [
            Message(role="user", content=GENERATE_CORE_STATS_INSTRUCTION),
            Message(role="assistant", content=f"Core Stats Defined."),
            Message(role="user", content=GENERATE_CONTAINERS_INSTRUCTION),
            Message(role="assistant", content=collections_summary),
            Message(role="user", content=ORGANIZE_LAYOUT_INSTRUCTION)
        ]

        # In this step, we expect the LLM to echo back the objects with updated panel/group fields
        layout_res = self.llm.get_structured_response(
            self.static_system_prompt,
            history_layout,
            LayoutAssignment
        )

        # --- STEP 4: PROCEDURES ---
        self._update_status("Phase 4: Extracting Game Logic...")
        class GameModes(BaseModel): names: List[str]
        
        # Use clean context for logic to avoid pollution from schema JSON
        logic_context = f"Target Game: {meta_res.name}\\n"
        
        modes = self.llm.get_structured_response(
            self.static_system_prompt, 
            [Message(role="user", content=logic_context + IDENTIFY_MODES_INSTRUCTION)], 
            GameModes
        )
        
        loops = GameLoopConfig()
        for mode in (modes.names[:6] if modes else []):
            self._update_status(f"Extracting Procedure: {mode}...")
            try:
                proc = self.llm.get_structured_response(
                    self.static_system_prompt, 
                    [Message(role="user", content=logic_context + EXTRACT_PROCEDURE_INSTRUCTION.format(mode_name=mode))], 
                    ProcedureDef
                )
                m = mode.lower()
                if "combat" in m or "encounter" in m: loops.encounter[mode] = proc
                elif "exploration" in m or "travel" in m: loops.exploration[mode] = proc
                elif "social" in m: loops.social[mode] = proc
                elif "downtime" in m: loops.downtime[mode] = proc
                else: loops.misc[mode] = proc
            except: pass

        # --- STEP 5: MECHANICS ---
        self._update_status("Phase 5: Indexing Mechanics...")
        class MechDict(BaseModel): items: dict[str, RuleEntry]
        
        mech_res = self.llm.get_structured_response(
            self.static_system_prompt, 
            [Message(role="user", content=logic_context + GENERATE_MECHANICS_INSTRUCTION)], 
            MechDict
        )

        # --- ASSEMBLY ---
        self._update_status("Finalizing Template...")

        ruleset = Ruleset(
            meta={"name": meta_res.name, "genre": meta_res.genre},
            physics=PhysicsConfig(
                dice_notation=meta_res.dice_notation,
                roll_mechanic=meta_res.roll_mechanic,
                success_condition="See Rules",
                crit_rules="See Rules"
            ),
            gameplay_procedures=loops,
            rules=mech_res.items
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
            collections=final_collections
        )

        return ruleset, template
"""

# ==============================================================================
# 4. SCAFFOLDING: MATCHING NEW SCHEMA
# ==============================================================================
FILES["app/setup/scaffolding.py"] = """import json
import logging
from app.models.ruleset import Ruleset, PhysicsConfig
from app.models.stat_block import (
    StatBlockTemplate, StatValue, StatGauge, StatCollection, CollectionItemField
)
from app.setup.setup_manifest import SetupManifest

logger = logging.getLogger(__name__)

def _get_default_scaffolding():
    \"\"\"Returns default scaffolding with Flattened Layout.\"\"\"
    ruleset = Ruleset(
        meta={"name": "Simple RPG", "genre": "Fantasy"},
        physics=PhysicsConfig(
            dice_notation="1d20",
            roll_mechanic="Roll + Mod >= 10",
            success_condition=">= 10",
            crit_rules="Nat 20"
        )
    )
    
    values = {
        "str": StatValue(id="str", label="Strength", widget="number", panel="sidebar", group="Attributes", default=10),
        "dex": StatValue(id="dex", label="Dexterity", widget="number", panel="sidebar", group="Attributes", default=10),
        "ac": StatValue(id="ac", label="Armor Class", widget="number", panel="main", group="Combat", default=10, calculation="10 + ((dex - 10) // 2)"),
        "class": StatValue(id="class", label="Class", data_type="string", widget="text_line", panel="header", group="Identity", default="Adventurer")
    }

    gauges = {
        "hp": StatGauge(id="hp", label="Hit Points", widget="bar", panel="header", group="Vitals", min_val=0, max_formula="10 + ((str - 10) // 2)")
    }

    collections = {
        "inventory": StatCollection(
            id="inventory", 
            label="Backpack", 
            panel="equipment",
            group="Gear",
            item_schema=[
                CollectionItemField(key="name", label="Item", data_type="string"),
                CollectionItemField(key="qty", label="Qty", data_type="integer", widget="number")
            ]
        )
    }

    template = StatBlockTemplate(
        template_name="Adventurer",
        values=values,
        gauges=gauges,
        collections=collections
    )
    
    return ruleset, template

def inject_setup_scaffolding(session_id: int, prompt_manifest_json: str, db_manager):
    \"\"\"Injects scaffolding into DB.\"\"\"
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
        
        entity_data = {
            "name": "Player",
            "template_id": st_id,
            "values": {k: v.default for k, v in st_model.values.items()},
            "gauges": {k: {"current": 10, "max": 10} for k, v in st_model.gauges.items()},
            "collections": {k: [] for k, v in st_model.collections.items()}
        }
        
        db_manager.game_state.set_entity(session_id, "character", "player", entity_data)
        
        SetupManifest(db_manager).update_manifest(session_id, {
            "ruleset_id": rs_id,
            "stat_template_id": st_id,
            "genre": ruleset_model.meta.get("genre", "Generic"),
            "tone": ruleset_model.meta.get("tone", "Neutral")
        })

    except Exception as e:
        logger.error(f"Error during scaffolding injection: {e}", exc_info=True)
"""


def apply_update():
    print("ðŸš€ Applying Flattened Layout & Strict Procedures...")
    for filepath, content in FILES.items():
        filepath = filepath.replace("/", os.sep)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        print(f"ðŸ“  Updating {filepath}...")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    print("âœ… Done.")


if __name__ == "__main__":
    apply_update()
