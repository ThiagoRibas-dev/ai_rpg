import json
import logging
import datetime
from typing import Any, Dict, Optional

from app.models.session import Session
from app.models.game_session import GameSession
from app.models.ruleset import Ruleset
from app.prefabs.manifest import SystemManifest
from app.setup.scaffolding import get_default_scaffolding
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
        prompt: Any,
        world_data: Any,
        opening_crawl: str,
        generate_crawl: bool = True,
        # Legacy/Fallback args
        char_data: Any = None,
        sheet_spec: Optional[Any] = None,
        sheet_values: Optional[Dict] = None,
    ) -> GameSession:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")

        # Determine Name
        c_name = "Player"
        if sheet_values and "identity" in sheet_values:
            c_name = sheet_values["identity"].get("name", "Player")
        elif hasattr(char_data, "name"):
            c_name = char_data.name

        session_name = f"{timestamp} - {c_name}"
        clean_session = Session("session_new")

        # Inject Rules Text
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

        # --- UNIFIED PIPELINE ---

        # 1. Resolve Spec & Values
        final_spec = sheet_spec
        final_values = sheet_values or {}

        # If no spec provided (legacy or failure), use default scaffolding
        if not final_spec:
            default_ruleset, default_spec = get_default_scaffolding()
            final_spec = default_spec

            # If we have legacy char_data, try to map it to the default spec
            if char_data:
                final_values = self._map_legacy_char_data(char_data, default_spec)
            else:
                # Minimal default values
                final_values = {"identity": {"name": c_name}, "attributes": {"str": 10}}

        # 2. Apply Scaffolding (Rules, Templates, Manifests)
        self._apply_scaffolding(
            game_session.id, prompt, final_spec, final_values, c_name
        )

        # 3. Apply World
        self._apply_world_extraction(game_session.id, world_data)

        game_session.game_mode = "GAMEPLAY"
        self.db.sessions.update(game_session)

        return game_session

    def _map_legacy_char_data(self, char_data, spec):
        """Helper to map old WorldGen char_data to new Sheet Values."""
        values = {
            "identity": {
                "name": getattr(char_data, "name", "Player"),
                "description": getattr(char_data, "visual_description", ""),
            },
            "attributes": {},
            "inventory": {"backpack": []},
        }

        # Try to dump stats into attributes
        if hasattr(char_data, "suggested_stats") and isinstance(
            char_data.suggested_stats, dict
        ):
            values["attributes"] = char_data.suggested_stats

        # Inventory
        if hasattr(char_data, "inventory") and isinstance(char_data.inventory, list):
            for item in char_data.inventory:
                values["inventory"]["backpack"].append({"name": item, "qty": 1})

        return values

    def _apply_scaffolding(
        self, session_id: int, prompt: Any, spec: Any, values: Dict, char_name: str
    ):
        # --- 1. LEGACY LAYER (Ruleset & StatTemplate) ---
        # We still need this for the CharacterInspector (UI) to work

        ruleset = None
        base_rules = []
        vocab_data = None
        manifest_data = None

        # Try to parse the Prompt's template_manifest
        if prompt.template_manifest:
            try:
                data = json.loads(prompt.template_manifest)
                manifest_data = data  # Store raw dict for Manifest logic

                # Legacy extraction for Ruleset table
                if "ruleset" in data:
                    ruleset = Ruleset(**data["ruleset"])
                elif "engine" in data:
                    # It's a SystemManifest JSON, not a Ruleset JSON.
                    # We need to construct a legacy Ruleset from it for backward compat if needed.
                    # Or better yet, rely on the Manifest logic below.
                    pass

                if "base_rules" in data:
                    base_rules = data["base_rules"]
                if "vocabulary" in data:
                    vocab_data = data["vocabulary"]
            except Exception:
                pass

        if not ruleset:
            ruleset, _ = get_default_scaffolding()
            ruleset.meta["name"] = prompt.name

        # Persist Ruleset (UPSERT Logic)
        target_name = ruleset.meta.get("name")
        existing_rs = self.db.rulesets.get_by_name(target_name)

        if existing_rs:
            rs_id = existing_rs["id"]
            self.db.rulesets.update(rs_id, ruleset)
        else:
            rs_id = self.db.rulesets.create(ruleset)

        # Persist Template (The Spec)
        st_id = self.db.stat_templates.create(rs_id, spec)

        # --- 2. MANIFEST LAYER (The New "Lego" Brain) ---
        manifest_db_id = None

        if manifest_data:
            try:
                # Try to parse as SystemManifest (New Format)
                if "fields" in manifest_data and "engine" in manifest_data:
                    # It's a SystemManifest!
                    sys_manifest = SystemManifest.from_dict(manifest_data)

                    # Upsert into manifests table
                    # We use system_id to check for existence
                    existing_m = self.db.manifests.get_by_system_id(sys_manifest.id)
                    if existing_m:
                        self.db.manifests.update(existing_m.id, sys_manifest)
                        manifest_db_id = existing_m.id
                    else:
                        manifest_db_id = self.db.manifests.create(sys_manifest)

            except Exception as e:
                logger.warning(f"Failed to process SystemManifest from prompt: {e}")

        # --- 3. CREATE PLAYER ENTITY ---
        entity_data = values.copy()
        entity_data["name"] = char_name
        entity_data["template_id"] = st_id
        entity_data["scene_state"] = {"zone_id": None, "is_hidden": False}

        # Ensure all categories exist
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
            if cat not in entity_data:
                entity_data[cat] = {}

        set_entity(session_id, self.db, "character", "player", entity_data)

        # --- 4. UPDATE SETUP MANIFEST (Link everything) ---
        manifest_update = {
            "ruleset_id": rs_id,
            "stat_template_id": st_id,
            "player_character": {"name": char_name},
        }

        # CRITICAL FIX: Save the manifest_id so ReActTurnManager loads the correct system
        if manifest_db_id:
            manifest_update["manifest_id"] = manifest_db_id

        if vocab_data:
            manifest_update["vocabulary"] = vocab_data

        SetupManifestService(self.db).update_manifest(session_id, manifest_update)

        # --- 5. Index Base Rules (Memories) ---
        for rule in base_rules:
            mem = self.db.memories.create(
                session_id=session_id,
                kind="rule",
                content=rule.get("content", ""),
                tags=rule.get("tags", []),
                priority=3,
            )
            if self.vs:
                try:
                    self.vs.upsert_memory(
                        session_id=session_id,
                        memory_id=mem.id,
                        text=mem.content,
                        kind=mem.kind,
                        tags=mem.tags_list(),
                        priority=mem.priority,
                    )
                except Exception:
                    pass

    def _apply_world_extraction(self, session_id: int, world_data: Any):
        SetupManifestService(self.db).update_manifest(
            session_id, {"genre": world_data.genre, "tone": world_data.tone}
        )

        # Location
        loc = world_data.starting_location
        loc_data = {
            "name": loc.name,
            "description_visual": loc.description_visual,
            "description_sensory": loc.description_sensory,
            "type": loc.type,
            "connections": {},
        }
        set_entity(session_id, self.db, "location", loc.key, loc_data)

        # Neighbors
        context = {"session_id": session_id, "db_manager": self.db}
        for neighbor in world_data.adjacent_locations:
            try:
                args = neighbor.model_dump()
                args["name_display"] = args.pop("name")
                location_create_handler(**args, **context)
            except Exception as e:
                logger.warning(
                    f"Failed to create neighbor location {neighbor.key}: {e}"
                )
                pass

        # Scene & NPCs
        scene = {"members": ["character:player"], "location_key": loc.key}

        for npc in world_data.initial_npcs:
            key = f"npc_{npc.name.lower().replace(' ', '_')}"
            self._create_npc_entity(
                session_id, key, npc, loc.key, disposition=npc.initial_disposition
            )
            scene["members"].append(f"character:{key}")

        set_entity(session_id, self.db, "scene", "active_scene", scene)

        # Lore
        for mem in world_data.lore:
            new_mem = self.db.memories.create(
                session_id, mem.kind, mem.content, mem.priority, mem.tags
            )
            if self.vs:
                try:
                    self.vs.upsert_memory(
                        session_id,
                        new_mem.id,
                        new_mem.content,
                        new_mem.kind,
                        new_mem.tags_list(),
                        new_mem.priority,
                    )
                except Exception as e:
                    logger.warning(f"Failed to index lore memory {new_mem.id}: {e}")

    def _create_npc_entity(
        self,
        session_id: int,
        key: str,
        npc_data: Any,
        location_key: str,
        disposition="neutral",
    ):
        name = getattr(npc_data, "name", "Unknown")
        desc = getattr(npc_data, "visual_description", "")

        manifest = SetupManifestService(self.db).get_manifest(session_id)
        template_id = manifest.get("stat_template_id")

        npc_dict = {
            "name": name,
            "description": desc,
            "disposition": disposition,
            "location_key": location_key,
            "template_id": template_id,
            "attributes": {},
            "resources": {},
            "skills": {},
            "inventory": {},
            "scene_state": {"zone_id": None},
        }

        if template_id:
            npc_dict["resources"] = {"hp": {"current": 10, "max": 10}}

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
