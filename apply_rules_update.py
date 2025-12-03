import os
import sys


def write_file(path, content):
    """Writes content to a file, ensuring directory exists."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip())
    print(f"✅ Updated: {path}")


def delete_file(path):
    """Deletes a file if it exists."""
    if os.path.exists(path):
        os.remove(path)
        print(f"🗑️ Deleted: {path}")
    else:
        print(f"⚠️ File not found (skip delete): {path}")


# ==============================================================================
# 1. CREATE app/setup/rules_generator.py
# ==============================================================================
rules_generator_content = """
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
        base_prompt = f"{TEMPLATE_GENERATION_SYSTEM_PROMPT}\\n\\n# RULES REFERENCE\\n{rules_text}"
        
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
"""

# ==============================================================================
# 2. UPDATE app/gui/dialogs/prompt_editor.py
# ==============================================================================
prompt_editor_content = """
from nicegui import ui
import json
import asyncio
from app.models.prompt import Prompt
from app.setup.rules_generator import RulesGenerator

class PromptEditorDialog:
    def __init__(self, db_manager, orchestrator, prompt: Prompt = None, on_save=None):
        self.db = db_manager
        self.orchestrator = orchestrator
        self.prompt = prompt
        self.on_save = on_save
        self.dialog = ui.dialog()

        # State
        self.name = prompt.name if prompt else "New System"
        self.content = prompt.content if prompt else "You are a Game Master for..."
        self.rules = prompt.rules_document if prompt else ""
        
        # Load existing ruleset JSON if present
        self.ruleset_json = "{}"
        if prompt and prompt.template_manifest:
            try:
                # Check if it's wrapped in 'ruleset' key or raw
                data = json.loads(prompt.template_manifest)
                if "ruleset" in data:
                    self.ruleset_json = json.dumps(data["ruleset"], indent=2)
                else:
                    self.ruleset_json = prompt.template_manifest
            except:
                pass

        # UI Refs
        self.status_label = None
        self.gen_btn = None

    def open(self):
        with self.dialog, ui.card().classes('w-[1200px] h-[800px] bg-slate-900 border border-slate-700 p-0'):
            
            # Header
            with ui.row().classes('w-full bg-slate-950 p-4 justify-between items-center border-b border-slate-700'):
                title = "Edit Prompt" if self.prompt else "Create Prompt"
                ui.label(title).classes('text-xl font-bold text-white')
                ui.button(icon='close', on_click=self.dialog.close).props('flat dense round')

            # Body: Split View
            with ui.row().classes('w-full h-full gap-0'):
                
                # LEFT COLUMN: Text Inputs
                with ui.column().classes('w-1/2 h-full p-4 border-r border-slate-800 scroll-y gap-4'):
                    ui.input(label="System Name").bind_value(self, 'name').classes('w-full')
                    
                    ui.label("System Instruction (The Persona)").classes('text-xs font-bold text-gray-500 uppercase mt-2')
                    ui.textarea(placeholder="You are the GM...").bind_value(self, 'content').classes('w-full').props('rows=4 outlined')
                    
                    ui.label("Rules Document (The Knowledge Base)").classes('text-xs font-bold text-gray-500 uppercase mt-2')
                    ui.label("Paste raw text rules here.").classes('text-xs text-gray-600 italic')
                    ui.textarea(placeholder="Paste rules text here...").bind_value(self, 'rules').classes('w-full flex-grow').props('rows=10 outlined')

                # RIGHT COLUMN: Rules Extraction
                with ui.column().classes('w-1/2 h-full p-4 flex flex-col'):
                    ui.label("System Mechanics (JSON)").classes('text-xs font-bold text-gray-500 uppercase')
                    ui.label("Extracted logic used by the Game Engine (Dice, Procedures).").classes('text-xs text-gray-600 italic')
                    
                    # Toolbar
                    with ui.row().classes('w-full items-center gap-2 mb-2'):
                        self.gen_btn = ui.button("Extract Rules", on_click=self.run_extraction) \\
                            .classes('bg-purple-700 text-xs').props('icon=auto_awesome')
                        self.status_label = ui.label("").classes('text-xs text-green-400')

                    # Editor
                    ui.textarea().bind_value(self, 'ruleset_json').classes('w-full h-full font-mono text-xs') \\
                        .props('outlined input-class="h-full"')

            # Footer
            with ui.row().classes('w-full bg-slate-950 p-4 justify-end gap-2 border-t border-slate-700 absolute bottom-0'):
                ui.button("Cancel", on_click=self.dialog.close).props('flat')
                ui.button("Save System", on_click=self.save).classes('bg-green-600')

        self.dialog.open()

    async def run_extraction(self):
        if not self.rules.strip():
            ui.notify("Please enter Rules text first.", type='warning')
            return

        self.gen_btn.disable()
        self.status_label.set_text("Initializing Extraction...")
        
        await asyncio.to_thread(self._execute_extraction)
        
        self.gen_btn.enable()

    def _execute_extraction(self):
        connector = self.orchestrator._get_llm_connector()
        service = RulesGenerator(connector, status_callback=self._update_status)
        
        try:
            ruleset = service.generate_ruleset(self.rules)
            self.ruleset_json = ruleset.model_dump_json(indent=2)
            self._update_status("Extraction Complete!")
        except Exception as e:
            self._update_status(f"Error: {str(e)}")

    def _update_status(self, msg):
        self.status_label.set_text(msg)

    def save(self):
        if not self.name or not self.content:
            ui.notify("Name and System Instruction are required.", type='negative')
            return

        # Prepare Manifest
        manifest_str = "{}"
        if self.ruleset_json.strip():
            try:
                # Validate JSON
                data = json.loads(self.ruleset_json)
                # Wrap in 'ruleset' key if not already
                if "ruleset" not in data:
                    final_data = {"ruleset": data}
                else:
                    final_data = data
                manifest_str = json.dumps(final_data)
            except json.JSONDecodeError:
                ui.notify("Invalid JSON in Mechanics field.", type='negative')
                return

        if self.prompt:
            # Update
            self.prompt.name = self.name
            self.prompt.content = self.content
            self.prompt.rules_document = self.rules
            self.prompt.template_manifest = manifest_str
            self.db.prompts.update(self.prompt)
            ui.notify(f"Updated '{self.name}'")
        else:
            # Create
            self.db.prompts.create(
                self.name, self.content, self.rules, manifest_str
            )
            ui.notify(f"Created '{self.name}'")

        if self.on_save: self.on_save()
        self.dialog.close()
"""

# ==============================================================================
# 3. UPDATE app/services/game_setup_service.py
# ==============================================================================
game_setup_content = """
import json
import logging
import datetime
from typing import Any, Dict, Optional

from app.models.session import Session
from app.models.game_session import GameSession
from app.models.ruleset import Ruleset, PhysicsConfig
from app.setup.scaffolding import inject_setup_scaffolding
from app.services.state_service import get_entity, set_entity, get_all_of_type
from app.tools.builtin.location_create import handler as location_create_handler
from app.setup.setup_manifest import SetupManifest

logger = logging.getLogger(__name__)


class GameSetupService:
    \"\"\"
    Handles the creation of a new game session.
    \"\"\"

    def __init__(self, db_manager):
        self.db = db_manager

    def create_game(
        self,
        prompt: Any,
        char_data: Any,
        world_data: Any,
        opening_crawl: str,
        generate_crawl: bool = True,
        sheet_spec: Optional[Any] = None,
        sheet_values: Optional[Dict] = None,
    ) -> GameSession:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")

        # Determine name
        c_name = "Player"
        if hasattr(char_data, "name"):
            c_name = char_data.name
        elif isinstance(sheet_values, dict):
            if "identity" in sheet_values and "name" in sheet_values["identity"]:
                c_name = sheet_values["identity"]["name"]

        session_name = f"{timestamp} - {c_name}"

        # 1. Prepare Initial Session Data (History)
        clean_session = Session("session_new")

        # --- CRITICAL FIX: INJECT RULES INTO SYSTEM PROMPT ---
        # We combine the Persona (content) with the Rules (rules_document)
        full_system_prompt = prompt.content
        if prompt.rules_document:
            full_system_prompt += "\\n\\n# GAME RULES REFERENCE\\n" + prompt.rules_document

        clean_session.system_prompt = full_system_prompt
        # -----------------------------------------------------

        if generate_crawl and opening_crawl:
            clean_session.add_message("assistant", opening_crawl)
        else:
            clean_session.add_message(
                "system",
                "Session initialized. Waiting for player input.",
            )

        # 2. Create DB Entry
        setup_snapshot = {
            "world_data": world_data.model_dump()
            if hasattr(world_data, "model_dump")
            else str(world_data),
            "opening_crawl": opening_crawl,
        }

        game_session = self.db.sessions.create(
            name=session_name,
            session_data=clean_session.to_json(),
            prompt_id=prompt.id,
            setup_phase_data=json.dumps(setup_snapshot),
        )

        # 3. Inject Scaffolding
        if sheet_spec and sheet_values:
            self._apply_dynamic_scaffolding(
                game_session.id, prompt, sheet_spec, sheet_values, c_name
            )
        else:
            inject_setup_scaffolding(game_session.id, prompt.template_manifest, self.db)
            self._apply_character_extraction(game_session.id, char_data)

        # 4. Apply World Extraction
        self._apply_world_extraction(game_session.id, world_data)

        # 5. Set Mode
        game_session.game_mode = "GAMEPLAY"
        self.db.sessions.update(game_session)

        logger.info(
            f"Game '{session_name}' created successfully (ID: {game_session.id})"
        )
        return game_session

    def _apply_dynamic_scaffolding(
        self, session_id: int, prompt: Any, spec: Any, values: Dict, char_name: str
    ):
        # 1. Try to load Pre-Extracted Ruleset from Prompt Manifest
        ruleset = None
        if prompt.template_manifest:
            try:
                data = json.loads(prompt.template_manifest)
                if "ruleset" in data:
                    ruleset = Ruleset(**data["ruleset"])
            except Exception as e:
                logger.warning(f"Failed to load ruleset from manifest: {e}")
        
        # 2. Fallback to Stub if missing
        if not ruleset:
            ruleset = Ruleset(
                meta={"name": prompt.name, "genre": "Custom"},
                physics=PhysicsConfig(
                    dice_notation="1d20",
                    roll_mechanic="See System Prompt",
                    success_condition="See System Prompt",
                    crit_rules="See System Prompt",
                )
            )
        
        # 3. Create Ruleset in DB
        rs_id = self.db.rulesets.create(ruleset)

        # 4. Create Template
        st_id = self.db.stat_templates.create(rs_id, spec)

        # 5. Create Entity
        entity_data = values.copy()
        entity_data["name"] = char_name
        entity_data["template_id"] = st_id
        entity_data["location_key"] = None
        entity_data["scene_state"] = {"zone_id": None, "is_hidden": False}

        for cat in [
            "meta",
            "identity",
            "attributes",
            "skills",
            "resources",
            "features",
            "inventory",
            "connections",
            "narrative",
            "progression",
        ]:
            if cat not in entity_data:
                entity_data[cat] = {}

        set_entity(session_id, self.db, "character", "player", entity_data)

        SetupManifest(self.db).update_manifest(
            session_id,
            {
                "ruleset_id": rs_id,
                "stat_template_id": st_id,
                "player_character": {"name": char_name},
            },
        )

    def _apply_character_extraction(self, session_id: int, char_data: Any):
        # Legacy logic for backward compatibility
        player = get_entity(session_id, self.db, "character", "player")
        if not player:
            return

        player["name"] = char_data.name
        player["description"] = char_data.visual_description

        funds = player.setdefault("fundamentals", {})
        gauges = player.setdefault("gauges", {})

        for stat_name, val in char_data.suggested_stats.items():
            if stat_name in funds:
                funds[stat_name] = val
                continue
            if stat_name in gauges:
                gauges[stat_name]["current"] = val
                continue

            found = False
            for k in funds.keys():
                if k.lower() == stat_name.lower():
                    funds[k] = val
                    found = True
                    break
            if found:
                continue

            for k in gauges.keys():
                if k.lower() == stat_name.lower():
                    gauges[k]["current"] = val
                    break

        cols = player.setdefault("collections", {})
        target_col = "inventory"
        if "inventory" not in cols:
            if cols:
                target_col = next(iter(cols))
            else:
                cols["inventory"] = []

        target_list = cols.setdefault(target_col, [])
        for item_str in char_data.inventory:
            target_list.append({"name": item_str, "qty": 1})

        player["scene_state"] = {"zone_id": None, "is_hidden": False}
        set_entity(session_id, self.db, "character", "player", player)

        for npc in char_data.companions:
            key = f"companion_{npc.name_display.lower().replace(' ', '_')}"
            self._create_npc_entity(session_id, key, npc, disposition="friendly")

    def _apply_world_extraction(self, session_id: int, world_data: Any):
        SetupManifest(self.db).update_manifest(
            session_id, {"genre": world_data.genre, "tone": world_data.tone}
        )

        loc = world_data.starting_location
        loc_data = {
            "name": loc.name_display,
            "description_visual": loc.description_visual,
            "description_sensory": loc.description_sensory,
            "type": loc.type,
            "connections": {},
        }
        set_entity(session_id, self.db, "location", loc.key, loc_data)

        context = {"session_id": session_id, "db_manager": self.db}
        for neighbor in world_data.adjacent_locations:
            args = neighbor.model_dump(exclude={"name"})
            try:
                location_create_handler(**args, **context)
            except Exception as e:
                logger.error(f"Failed to create adjacent location {neighbor.key}: {e}")

        scene = get_entity(session_id, self.db, "scene", "active_scene")
        if not scene:
            scene = {"members": [], "state_tags": []}

        scene["location_key"] = loc.key

        scene_members = ["character:player"]
        for npc in world_data.initial_npcs:
            key = f"npc_{npc.name_display.lower().replace(' ', '_')}"
            npc.location_key = loc.key
            self._create_npc_entity(
                session_id, key, npc, disposition=npc.initial_disposition
            )
            scene_members.append(f"character:{key}")

        all_chars = get_all_of_type(session_id, self.db, "character")
        for key, data in all_chars.items():
            if key.startswith("companion_"):
                data["location_key"] = loc.key
                set_entity(session_id, self.db, "character", key, data)
                scene_members.append(f"character:{key}")

        scene["members"] = scene_members
        set_entity(session_id, self.db, "scene", "active_scene", scene)

        for mem in world_data.lore:
            self.db.memories.create(
                session_id, mem.kind, mem.content, mem.priority, mem.tags
            )

    def _create_npc_entity(
        self, session_id: int, key: str, npc_model: Any, disposition="neutral"
    ):
        npc_data = {
            "name": npc_model.name_display,
            "description": npc_model.visual_description,
            "disposition": disposition,
            "location_key": npc_model.location_key,
            "template_id": None,
            "gauges": {"hp": {"current": 10, "max": 10}},
            "scene_state": {"zone_id": None, "is_hidden": False},
        }
        set_entity(session_id, self.db, "character", key, npc_data)

        profile_data = {
            "personality_traits": [],
            "motivations": ["Exist"],
            "directive": "Patrol" if disposition == "hostile" else "Wander",
            "relationships": {},
            "last_updated_time": "Day 1, Dawn",
        }
        set_entity(session_id, self.db, "npc_profile", key, profile_data)
"""

if __name__ == "__main__":
    write_file("app/setup/rules_generator.py", rules_generator_content)
    write_file("app/gui/dialogs/prompt_editor.py", prompt_editor_content)
    write_file("app/services/game_setup_service.py", game_setup_content)

    # Cleanup old file
    delete_file("app/setup/template_generation_service.py")

    print("\\n🚀 Rules Fix Applied Successfully.")
