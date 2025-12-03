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
    """
    Handles the creation of a new game session.
    """

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
            full_system_prompt += "\n\n# GAME RULES REFERENCE\n" + prompt.rules_document

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
        # 1. Create Ruleset
        ruleset = Ruleset(
            meta={"name": prompt.name, "genre": "Custom"},
            physics=PhysicsConfig(
                dice_notation="1d20",
                roll_mechanic="See System Prompt",
                success_condition="See System Prompt",
                crit_rules="See System Prompt",
            ),
        )
        rs_id = self.db.rulesets.create(ruleset)

        # 2. Create Template
        st_id = self.db.stat_templates.create(rs_id, spec)

        # 3. Create Entity
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
        # Legacy
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
