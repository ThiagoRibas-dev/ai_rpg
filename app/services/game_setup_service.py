import json
import logging
import datetime
from typing import Any, Dict

from app.models.session import Session
from app.models.game_session import GameSession
from app.setup.scaffolding import inject_setup_scaffolding
from app.services.state_service import get_entity, set_entity, get_all_of_type
from app.tools.builtin.location_create import handler as location_create_handler

logger = logging.getLogger(__name__)

class GameSetupService:
    """
    Handles the creation of a new game session, including:
    1. Creating the Session DB entry.
    2. Injecting Rules/Stats scaffolding.
    3. Applying LLM-extracted Character & World data to the Game State.
    """

    def __init__(self, db_manager):
        self.db = db_manager

    def create_game(
        self,
        prompt: Any,
        char_data: Any,
        world_data: Any,
        opening_crawl: str,
        generate_crawl: bool = True
    ) -> GameSession:
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
        session_name = f"{timestamp} - {char_data.name}"

        # 1. Prepare Initial Session Data (History)
        clean_session = Session(f"session_new")
        clean_session.system_prompt = prompt.content
        
        if generate_crawl and opening_crawl:
            clean_session.add_message("assistant", opening_crawl)
        else:
            clean_session.add_message(
                "system",
                f"Session initialized at {world_data.starting_location.name_display}. Waiting for player input.",
            )

        # 2. Create DB Entry
        # We store the extraction data in setup_phase_data for reference/debugging
        setup_data = {
            "initial_state": {
                "character_data": char_data.model_dump(),
                "world_data": world_data.model_dump(),
                "opening_crawl": opening_crawl,
            }
        }
        
        game_session = self.db.sessions.create(
            name=session_name,
            session_data=clean_session.to_json(),
            prompt_id=prompt.id,
            setup_phase_data=json.dumps(setup_data)
        )
        
        # 3. Inject Scaffolding (Rulesets & Templates)
        inject_setup_scaffolding(game_session.id, prompt.template_manifest, self.db)

        # 4. Apply Extractions
        self._apply_world_extraction(game_session.id, world_data)
        self._apply_character_extraction(game_session.id, char_data)

        # 5. Set Mode
        game_session.game_mode = "GAMEPLAY"
        self.db.sessions.update(game_session)
        
        logger.info(f"Game '{session_name}' created successfully (ID: {game_session.id})")
        return game_session

    def _apply_character_extraction(self, session_id: int, char_data: Any):
        player = get_entity(session_id, self.db, "character", "player")
        if not player:
            return

        player["name"] = char_data.name
        player["description"] = char_data.visual_description

        # Map Suggested Stats to Fundamentals/Gauges
        funds = player.setdefault("fundamentals", {})
        gauges = player.setdefault("gauges", {})

        for stat_name, val in char_data.suggested_stats.items():
            # Try exact match in Fundamentals
            if stat_name in funds:
                funds[stat_name] = val
                continue

            # Try exact match in Gauges (Set Current)
            if stat_name in gauges:
                gauges[stat_name]["current"] = val
                continue

            # Fuzzy match (Case-insensitive)
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

        # Map Inventory
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

        # Spawn Companions
        for npc in char_data.companions:
            key = f"companion_{npc.name_display.lower().replace(' ', '_')}"
            self._create_npc_entity(session_id, key, npc, disposition="friendly")

    def _apply_world_extraction(self, session_id: int, world_data: Any):
        from app.setup.setup_manifest import SetupManifest
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

        # Create Neighbors
        context = {"session_id": session_id, "db_manager": self.db}
        for neighbor in world_data.adjacent_locations:
            args = neighbor.model_dump(exclude={"name"})
            try:
                location_create_handler(**args, **context)
            except Exception as e:
                logger.error(f"Failed to create adjacent location {neighbor.key}: {e}")

        # Update Scene
        scene = get_entity(session_id, self.db, "scene", "active_scene")
        if not scene:
             scene = {"members": [], "state_tags": []}
             
        scene["location_key"] = loc.key
        set_entity(session_id, self.db, "scene", "active_scene", scene)

        # Create Lore Memories
        for mem in world_data.lore:
            self.db.memories.create(
                session_id, mem.kind, mem.content, mem.priority, mem.tags
            )

        # Initial NPCs
        scene_members = ["character:player"]
        for npc in world_data.initial_npcs:
            key = f"npc_{npc.name_display.lower().replace(' ', '_')}"
            npc.location_key = loc.key
            self._create_npc_entity(
                session_id, key, npc, disposition=npc.initial_disposition
            )
            scene_members.append(f"character:{key}")

        # Update companions to be in scene
        all_chars = get_all_of_type(session_id, self.db, "character")
        for key, data in all_chars.items():
            if key.startswith("companion_"):
                data["location_key"] = loc.key
                set_entity(session_id, self.db, "character", key, data)
                scene_members.append(f"character:{key}")

        scene["members"] = scene_members
        scene["layout_type"] = "default"
        scene["zones"] = []
        set_entity(session_id, self.db, "scene", "active_scene", scene)

    def _create_npc_entity(self, session_id: int, key: str, npc_model: Any, disposition="neutral"):
        npc_data = {
            "name": npc_model.name_display,
            "description": npc_model.visual_description,
            "disposition": disposition,
            "location_key": npc_model.location_key,
            "template_id": None,
            "fundamentals": {},
            "derived": {},
            "gauges": {"hp": {"current": 10, "max": 10}},
            "collections": {"inventory": []},
            "scene_state": {"zone_id": None, "is_hidden": False},
        }
        set_entity(session_id, self.db, "character", key, npc_data)

        profile_data = {
            "personality_traits": [],
            "motivations": ["Exist in the world"],
            "directive": "Patrol area" if disposition == "hostile" else "Wander",
            "knowledge_tags": ["world_gen"],
            "relationships": {},
            "last_updated_time": "Day 1, Dawn",
        }
        set_entity(session_id, self.db, "npc_profile", key, profile_data)