import json
import logging
import datetime
from typing import Any, Dict

from app.models.session import Session
from app.models.game_session import GameSession
from app.prefabs.manifest import SystemManifest
from app.prefabs.validation import validate_entity
from app.services.state_service import set_entity
from app.tools.builtin.location_create import handler as location_create_handler
from app.setup.setup_manifest import SetupManifest as SetupManifestService

logger = logging.getLogger(__name__)


class GameSetupService:
    def __init__(self, db_manager, vector_store=None):
        self.db = db_manager
        self.vs = vector_store

    def create_game(
        self,
        prompt,
        world_data,
        opening_crawl,
        generate_crawl=True,
        char_data=None,
        sheet_spec=None,
        sheet_values=None,
    ) -> GameSession:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
        c_name = "Player"
        if sheet_values and "identity" in sheet_values:
            c_name = sheet_values["identity"].get("name", "Player")
        elif hasattr(char_data, "name"):
            c_name = char_data.name

        session_name = f"{timestamp} - {c_name}"
        clean_session = Session("session_new")
        full_sys = prompt.content
        if prompt.rules_document:
            full_sys += "\n\n# GAME RULES REFERENCE\n" + prompt.rules_document
        clean_session.system_prompt = full_sys

        if generate_crawl and opening_crawl:
            clean_session.add_message("assistant", opening_crawl)
        else:
            clean_session.add_message("system", "Session initialized.")

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

        # 1. Resolve Manifest
        manifest = None
        if prompt.template_manifest:
            try:
                manifest = SystemManifest.from_json(prompt.template_manifest)
            except Exception:
                pass

        if not manifest:
            from app.prefabs.manifest import create_empty_manifest

            manifest = create_empty_manifest("default", "Default System")

        # 2. Entity Creation
        entity_data = sheet_values or {}
        if not entity_data and char_data:
            entity_data = self._map_legacy_char_data(char_data)
        if "identity" not in entity_data:
            entity_data["identity"] = {"name": c_name}

        validated_entity, _ = validate_entity(entity_data, manifest)
        validated_entity["name"] = c_name
        validated_entity["scene_state"] = {"zone_id": None, "is_hidden": False}

        for cat in [
            "meta",
            "identity",
            "attributes",
            "skills",
            "resources",
            "inventory",
            "features",
            "progression",
            "connections",
            "narrative",
        ]:
            if cat not in validated_entity:
                validated_entity[cat] = {}

        set_entity(game_session.id, self.db, "character", "player", validated_entity)

        # 3. Register Manifest
        manifest_db_id = None
        existing_m = self.db.manifests.get_by_system_id(manifest.id)
        if existing_m:
            manifest_db_id = existing_m.id
        else:
            manifest_db_id = self.db.manifests.create(manifest)

        SetupManifestService(self.db).update_manifest(
            game_session.id,
            {
                "manifest_id": manifest_db_id,
                "player_character": {"name": c_name},
                "genre": world_data.genre,
                "tone": world_data.tone,
            },
        )

        # 4. Index Rules (RAG) - THE RESTORED LOGIC
        if manifest.rules:
            logger.info(f"Indexing {len(manifest.rules)} rules into Vector Store...")
            for rule in manifest.rules:
                mem = self.db.memories.create(
                    session_id=game_session.id,
                    kind="rule",
                    content=f"{rule.name}: {rule.content}",
                    tags=rule.tags + ["system_rule"],
                    priority=3,
                )
                if self.vs:
                    try:
                        self.vs.upsert_memory(
                            session_id=game_session.id,
                            memory_id=mem.id,
                            text=mem.content,
                            kind=mem.kind,
                            tags=mem.tags_list(),
                            priority=mem.priority,
                        )
                    except Exception as e:
                        logger.warning(f"VS Indexing failed for rule {mem.id}: {e}")

        # 5. World
        self._apply_world_extraction(game_session.id, world_data, manifest_db_id)

        game_session.game_mode = "GAMEPLAY"
        self.db.sessions.update(game_session)
        return game_session

    def _map_legacy_char_data(self, char_data) -> Dict:
        values = {
            "identity": {"name": getattr(char_data, "name", "Player")},
            "attributes": {},
            "inventory": {"backpack": []},
        }
        if hasattr(char_data, "suggested_stats") and isinstance(
            char_data.suggested_stats, dict
        ):
            values["attributes"] = char_data.suggested_stats
        if hasattr(char_data, "inventory") and isinstance(char_data.inventory, list):
            for item in char_data.inventory:
                values["inventory"]["backpack"].append({"name": item, "qty": 1})
        return values

    def _apply_world_extraction(
        self, session_id: int, world_data: Any, manifest_id: int
    ):
        loc = world_data.starting_location
        loc_data = {
            "name": loc.name,
            "description_visual": loc.description_visual,
            "description_sensory": loc.description_sensory,
            "type": loc.type,
            "connections": {},
        }
        set_entity(session_id, self.db, "location", loc.key, loc_data)

        context = {"session_id": session_id, "db_manager": self.db}
        for neighbor in world_data.adjacent_locations:
            try:
                args = neighbor.model_dump()
                args["name_display"] = args.pop("name")
                location_create_handler(**args, **context)
            except Exception:
                pass

        scene = {"members": ["character:player"], "location_key": loc.key}
        for npc in world_data.initial_npcs:
            key = f"npc_{npc.name.lower().replace(' ', '_')}"
            self._create_npc_entity(
                session_id,
                key,
                npc,
                loc.key,
                manifest_id,
                disposition=npc.initial_disposition,
            )
            scene["members"].append(f"character:{key}")
        set_entity(session_id, self.db, "scene", "active_scene", scene)

        for mem in world_data.lore:
            try:
                self.db.memories.create(
                    session_id, mem.kind, mem.content, mem.priority, mem.tags
                )
            except Exception:
                pass

    def _create_npc_entity(
        self,
        session_id: int,
        key: str,
        npc_data: Any,
        location_key: str,
        manifest_id: int,
        disposition="neutral",
    ):
        npc_dict = {
            "name": getattr(npc_data, "name", "Unknown"),
            "description": getattr(npc_data, "visual_description", ""),
            "disposition": disposition,
            "location_key": location_key,
            "template_id": None,
            "attributes": {},
            "resources": {"hp": {"current": 10, "max": 10}},
            "skills": {},
            "inventory": {},
            "scene_state": {"zone_id": None},
        }
        set_entity(session_id, self.db, "character", key, npc_dict)
        set_entity(
            session_id,
            self.db,
            "npc_profile",
            key,
            {
                "personality_traits": [],
                "motivations": ["Exist"],
                "directive": "Wander",
                "relationships": {},
            },
        )
