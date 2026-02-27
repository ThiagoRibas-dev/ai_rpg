import logging
from typing import List, Optional
from app.models.session import Session
from app.models.game_session import GameSession
from app.models.message import Message
from app.prefabs.manifest import SystemManifest
from app.setup.setup_manifest import SetupManifest

class ContextBuilder:
    """
    Constructs the System Prompt and Dynamic Context for the LLM.
    Manifest-Aware Implementation (Lego Protocol).
    """
    def __init__(
        self,
        db_manager,
        vector_store,
        state_builder,
        mem_retriever,
        simulation_service,
        tool_registry = None,
        logger: logging.Logger | None = None,
        manifest: Optional[SystemManifest] = None
    ):
        self.db = db_manager
        self.vs = vector_store
        self.state_builder = state_builder
        self.mem_retriever = mem_retriever
        self.simulation_service = simulation_service
        self.tool_registry = tool_registry
        self.logger = logger or logging.getLogger(__name__)
        self.manifest = manifest

    def build_static_system_instruction(self, game_session: GameSession) -> str:
        """
        Builds the permanent system instruction (Rules, Engine, Vocabulary).
        """
        sections = []
        
        # 1. Core Persona
        session_data = Session.from_json(game_session.session_data)
        user_game_prompt = session_data.get_system_prompt()
        sections.append(user_game_prompt)

        # 2. Game System Rules (from Manifest)
        if self.manifest:
            sections.append(self._build_manifest_context())
        else:
            # Fallback for legacy/setup
            sections.append(self._build_legacy_rules(game_session))

        # 3. Tool Definitions (The Catalog)
        if self.tool_registry:
            sections.append(self._build_tool_definitions())
        
        # 4. Author's Note. Assumes the formatting will be done by the Player/User
        if game_session.authors_note:
            sections.append(game_session.authors_note)

        return "\n\n".join(sections)

    def build_dynamic_context(
        self,
        game_session: GameSession,
        chat_history: List[Message],
        rag_memories: Optional[dict] = None,
    ) -> str:
        """
        Builds the context that changes every turn (State, Narrative, Procedure).
        """
        sections = []

        # 1. Current State (Character Sheet, Location, Inventory)
        state_text = self.state_builder.build(game_session.id, self.manifest)
        if state_text:
            sections.append(f"# CURRENT STATE #\n{state_text}")

        # 2. Active Procedure (Combat/Exploration)
        # We haven't reimplemented the mode switching logic yet.
        # if self.manifest:
        #     current_mode = game_session.game_mode.lower()
        #     proc_text = self.manifest.get_procedure(current_mode)
        #     if proc_text:
        #         sections.append(f"# ACTIVE PROCEDURE: {current_mode.upper()}\n{proc_text}")

        # 3. Spatial Context
        spatial_context = self._build_spatial_context(game_session.id)
        if spatial_context:
            sections.append(spatial_context)

        return "\n\n".join(sections)

    def _build_manifest_context(self) -> str:
        """Generates the cheat sheet for the active game system."""
        lines = [f"# GAME SYSTEM: {self.manifest.name}"]
        
        # Engine (Dice, Success, Crit)
        lines.append(self.manifest.get_engine_text())
        
        # Valid Paths (The Vocabulary)
        lines.append(self.manifest.get_path_hints())
        
        return "\n".join(lines)
        
    def _build_tool_definitions(self) -> str:
        """Extracts tool names and descriptions from the registry."""
        if not self.tool_registry:
            return ""
        
        lines = ["# AVAILABLE TOOLS"]
        for schema in self.tool_registry.get_all_schemas():
            name = schema["name"]
            desc = schema["description"].strip()
            # Clean up docstring formatting
            desc = " ".join(desc.split())
            lines.append(f"- **{name}**: {desc}")
            
        return "\n".join(lines)

    def _build_legacy_rules(self, game_session) -> str:
        """Fallback for setup phase or missing manifest."""
        manifest_data = SetupManifest(self.db).get_manifest(game_session.id)
        ruleset_id = manifest_data.get("ruleset_id")
        if ruleset_id:
            ruleset = self.db.rulesets.get_by_id(ruleset_id)
            if ruleset:
                e = ruleset.engine
                return f"# ENGINE CONFIG\n- Dice: {e.dice_notation}\n- Mechanic: {e.roll_mechanic}"
        return ""

    def _build_spatial_context(self, session_id: int) -> str:
        try:
            scene = self.db.game_state.get_entity(session_id, "scene", "active_scene")
            if not scene:
                return ""
            lines = []
            loc_key = scene.get("location_key")
            if loc_key:
                location = self.db.game_state.get_entity(session_id, "location", loc_key)
                if location:
                    lines.append(f"# LOCATION: {location.get('name', 'Unknown')} ({loc_key}) #")
                    lines.append(location.get("description_visual", ""))
                    conns = location.get("connections", {})
                    if conns:
                        exits = [f"{d.upper()} -> {data.get('display_name')}" for d, data in conns.items()]
                        lines.append("Exits: " + ", ".join(exits))
            return "\n".join(lines)
        except Exception:
            return ""

    def get_truncated_history(self, session: Session, max_messages: int) -> List[Message]:
        history = session.get_history()
        return history[-max_messages:] if len(history) > max_messages else history
