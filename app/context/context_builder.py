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
        logger: logging.Logger | None = None,
        manifest: Optional[SystemManifest] = None
    ):
        self.db = db_manager
        self.vs = vector_store
        self.state_builder = state_builder
        self.mem_retriever = mem_retriever
        self.simulation_service = simulation_service
        self.logger = logger or logging.getLogger(__name__)
        self.manifest = manifest

    def _wrap_section(self, title: str, content: str, lang: str = "markdown") -> str:
        """Utility to encapsulate a section in a backtick block with a header."""
        if not content or not content.strip():
            return ""
        return f"### {title}\n```{lang}\n{content.strip()}\n```"

    def build_static_system_instruction(self, game_session: GameSession) -> str:
        """
        Builds the permanent system instruction (Rules, Engine, Vocabulary).
        """
        sections = []
        
        # 1. Core Persona (Plain Text)
        session_data = Session.from_json(game_session.session_data)
        user_game_prompt = session_data.get_system_prompt()
        sections.append(user_game_prompt)

        # 2. Game System Rules (Sectionalized)
        rules_content = ""
        if self.manifest:
            rules_content = self._build_manifest_context()
        else:
             # Fallback for legacy/setup
             rules_content = self._build_legacy_rules(game_session)
        
        if rules_content:
            sections.append(self._wrap_section("GAME RULES & SYSTEM", rules_content))
        
        # 3. Author's Note. Assumes the formatting will be done by the Player/User
        if game_session.authors_note:
            sections.append(self._wrap_section("AUTHOR'S NOTE", game_session.authors_note, lang="text"))

        return "\n\n".join(sections)

    def build_dynamic_context(
        self,
        game_session: GameSession,
        chat_history: List[Message],
        rag_memories: Optional[dict] = None,
    ) -> str:
        """
        Builds the context that changes every turn (State, Narrative, Procedure).
        Order: World Index -> Active Quests -> Current Scene -> Character Sheet.
        """
        sections = []

        # 1. World Index (The Directory)
        index_text = self._build_entity_index(game_session.id)
        if index_text:
            sections.append(self._wrap_section("WORLD INDEX", index_text))

        # 2. Active Quests
        quests_text = self.state_builder.build_active_quests(game_session.id)
        if quests_text:
            sections.append(self._wrap_section("ACTIVE QUESTS", quests_text))

        # 3. Current Scene (Unified Spatial + Roster)
        scene_text = self._build_scene_block(game_session.id)
        if scene_text:
            sections.append(self._wrap_section("CURRENT SCENE", scene_text))

        # 4. Character Sheet (The Player's Personal Stats)
        if self.manifest:
            char_text = self.state_builder.build_character_sheet(game_session.id, self.manifest)
            if char_text:
                sections.append(self._wrap_section("CHARACTER SHEET", char_text))

        return "\n\n".join(sections)

    def _build_manifest_context(self) -> str:
        """Generates the cheat sheet for the active game system."""
        lines = [f"# SYSTEM: {self.manifest.name}\n"]
        
        # Engine (Table-fied)
        lines.append(f"**Engine Configuration**\n{self.manifest.get_engine_table()}\n")
        
        # Valid Paths (The Vocabulary)
        lines.append(self.manifest.get_path_hints())
        
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

    def _build_entity_index(self, session_id: int) -> str:
        try:
            from app.services.entity_index import get_index, render_index
            index = get_index(session_id, self.db)
            if index:
                return render_index(index)
        except Exception:
            pass
        return ""

    def _build_scene_block(self, session_id: int) -> str:
        """Combines spatial description and scene roster into one coherent block."""
        parts = []
        
        # Spatial
        spatial = self._build_spatial_context(session_id)
        if spatial:
            parts.append(spatial)
            
        # Roster
        roster = self.state_builder.build_scene_roster(session_id)
        if roster:
            parts.append(f"**Present Characters / NPCs**:\n{roster}")
            
        return "\n\n".join(parts).strip()

    def get_truncated_history(self, session: Session, max_messages: int) -> List[Message]:
        history = session.get_history()
        return history[-max_messages:] if len(history) > max_messages else history
