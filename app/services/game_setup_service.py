import json
import logging
import datetime
from typing import Any, Dict, Optional

from app.models.session import Session
from app.models.game_session import GameSession
from app.prefabs.manifest import SystemManifest
from app.prefabs.validation import validate_entity
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
        # The Wizard passes these:
        char_data: Any = None, # Legacy
        sheet_spec: Optional[Any] = None, # Legacy UI spec (ignored in Lego protocol)
        sheet_values: Optional[Dict] = None, # The raw data from LLM
    ) -> GameSession:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")

        # 1. Determine Character Name
        c_name = "Player"
        if sheet_values and "identity" in sheet_values:
            c_name = sheet_values["identity"].get("name", "Player")
        elif hasattr(char_data, "name"):
            c_name = char_data.name

        session_name = f"{timestamp} - {c_name}"
        clean_session = Session("session_new")

        # 2. Inject Rules Text into System Prompt
        full_sys = prompt.content
        if prompt.rules_document:
            full_sys += "\n\n# GAME RULES REFERENCE\n" + prompt.rules_document
        clean_session.system_prompt = full_sys

        # 3. Add Opening Message
        if generate_crawl and opening_crawl:
            clean_session.add_message("assistant", opening_crawl)
        else:
            clean_session.add_message("system", "Session initialized.")

        # 4. Create Session Record
        setup_snapshot = {
            "world_data": world_data.model_dump() if hasattr(world_data, "model_dump") else str(world_data),
            "opening_crawl": opening_crawl,
        }

        game_session = self.db.sessions.create(
            name=session_name,
            session_data=clean_session.to_json(),
            prompt_id=prompt.id,
            setup_phase_data=json.dumps(setup_snapshot),
        )

        # --- LEGO PIPELINE EXECUTION ---

        # 5. Resolve Manifest (Source of Truth)
        manifest = None
        if prompt.template_manifest:
            try:
                manifest = SystemManifest.from_json(prompt.template_manifest)
            except Exception as e:
                logger.error(f"Failed to load manifest from prompt: {e}")

        # Fallback to default if no manifest found
        if not manifest:
            logger.warning("No manifest found in prompt. Using default scaffolding.")
            _, default_spec = get_default_scaffolding() # We ignore legacy ruleset object
            # We construct a minimal SystemManifest on the fly for validation compatibility
            # In a real scenario, we might just load dnd_5e from disk as fallback
            from app.prefabs.manifest import create_empty_manifest
            manifest = create_empty_manifest("default", "Default System")

        # 6. Prepare Entity Data
        entity_data = sheet_values or {}
        
        # Legacy fallback mapping
        if not entity_data and char_data:
            entity_data = self._map_legacy_char_data(char_data)
        
        # Ensure minimal structure
        if "identity" not in entity_data:
            entity_data["identity"] = {"name": c_name}

        # 7. RUN VALIDATION PIPELINE (The "Lego" Fix)
        # This calculates derived stats (formulas) and clamps values (max HP)
        # BEFORE the data ever touches the database.
        validated_entity, logs = validate_entity(entity_data, manifest)
        
        if logs:
            logger.info(f"Setup Validation Logs: {logs}")

        # 8. Persist Player Entity
        # Add metadata required by the engine
        validated_entity["name"] = c_name
        validated_entity["scene_state"] = {"zone_id": None, "is_hidden": False}
        
        # Ensure all categories exist (for UI safety)
        for cat in ["meta", "identity", "attributes", "skills", "resources", "inventory", "features", "progression", "connections", "narrative"]:
            if cat not in validated_entity:
                validated_entity[cat] = {}

        set_entity(game_session.id, self.db, "character", "player", validated_entity)

        # 9. Update Setup Manifest (Link Manifest ID)
        # We need to find the ID of this manifest in the DB or create it
        manifest_db_id = None
        existing_m = self.db.manifests.get_by_system_id(manifest.id)
        if existing_m:
            manifest_db_id = existing_m.id
        else:
            manifest_db_id = self.db.manifests.create(manifest)

        manifest_update = {
            "manifest_id": manifest_db_id,
            "player_character": {"name": c_name},
            "genre": world_data.genre,
            "tone": world_data.tone
        }
        SetupManifestService(self.db).update_manifest(game_session.id, manifest_update)

        # 10. Apply World Data
        self._apply_world_extraction(game_session.id, world_data, manifest_db_id)

        # 11. Finalize
        game_session.game_mode = "GAMEPLAY"
        self.db.sessions.update(game_session)

        return game_session

    def _map_legacy_char_data(self, char_data) -> Dict:
        """Helper to map old WorldGen char_data to new Sheet Values."""
        values = {
            "identity": {
                "name": getattr(char_data, "name", "Player"),
                "description": getattr(char_data, "visual_description", ""),
            },
            "attributes": {},
            "inventory": {"backpack": []},
        }
        if hasattr(char_data, "suggested_stats") and isinstance(char_data.suggested_stats, dict):
            values["attributes"] = char_data.suggested_stats
        if hasattr(char_data, "inventory") and isinstance(char_data.inventory, list):
            for item in char_data.inventory:
                values["inventory"]["backpack"].append({"name": item, "qty": 1})
        return values

    def _apply_world_extraction(self, session_id: int, world_data: Any, manifest_id: int):
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
            except Exception:
                pass

        # Scene & NPCs
        scene = {"members": ["character:player"], "location_key": loc.key}

        for npc in world_data.initial_npcs:
            key = f"npc_{npc.name.lower().replace(' ', '_')}"
            self._create_npc_entity(
                session_id, key, npc, loc.key, manifest_id, disposition=npc.initial_disposition
            )
            scene["members"].append(f"character:{key}")

        set_entity(session_id, self.db, "scene", "active_scene", scene)

        # Lore
        for mem in world_data.lore:
            try:
                self.db.memories.create(
                    session_id, mem.kind, mem.content, mem.priority, mem.tags
                )
                # Vector store indexing omitted for brevity, handled by Orchestrator usually
            except Exception as e:
                logger.warning(f"Failed to create lore memory: {e}")

    def _create_npc_entity(
        self,
        session_id: int,
        key: str,
        npc_data: Any,
        location_key: str,
        manifest_id: int,
        disposition="neutral",
    ):
        # We rely on the specialized tool handler logic or simple creation here.
        # Since we have the tool logic in `npc_spawn.py`, we can simulate it or just write direct.
        # Writing direct is safer to avoid circular dependencies.
        
        npc_dict = {
            "name": getattr(npc_data, "name", "Unknown"),
            "description": getattr(npc_data, "visual_description", ""),
            "disposition": disposition,
            "location_key": location_key,
            # We do NOT assign the player's manifest ID here directly unless we want them to use the full sheet.
            # Usually, we want a simplified sheet for NPCs.
            # But for consistency, if we have a valid manifest, we can link it.
            # The danger is "Wizard Goblin". 
            # We will leave `template_id` None, so `npc_spawn` logic (or runtime) uses Minimal fallback.
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
