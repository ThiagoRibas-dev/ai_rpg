import logging
from typing import List
from app.models.session import Session
from app.models.game_session import GameSession
from app.models.npc_profile import NpcProfile
from app.models.message import Message

class ContextBuilder:
    """Builds static and dynamic prompt components for caching optimization."""

    def __init__(
        self,
        db_manager,
        vector_store,
        state_builder,
        mem_retriever,
        turnmeta,
        logger: logging.Logger | None = None,
    ):
        self.db = db_manager
        self.vs = vector_store
        self.state_builder = state_builder
        self.mem_retriever = mem_retriever
        self.turnmeta = turnmeta
        self.logger = logger or logging.getLogger(__name__)

    def build_static_system_instruction(
        self,
        game_session: GameSession, # tool_schemas removed
        schema_ref: str = "",
    ) -> str:
        """
        Build the cacheable system instruction.
        Call this when:
        - Session starts
        - Session is loaded
        - Author's note is edited
        - Tool availability changes (this is now handled by the tool calling API, so the full schemas are not needed here)
        """
        sections = []

        # 1. User's game prompt (from Session.system_prompt, NOT history)
        session_data = Session.from_json(game_session.session_data)
        user_game_prompt = session_data.get_system_prompt()
        sections.append(user_game_prompt)

        # 2. ✅ NEW: Lean schema reference (if exists)
        if schema_ref:
            sections.append("# GAME MECHANICS REFERENCE")
            sections.append(schema_ref)
            sections.append("Use schema.query or state.query for detailed values.")


        # 4. Author's note (if exists)
        if game_session.authors_note:
            sections.append("# NOTE")
            sections.append(game_session.authors_note)

        return "\n\n".join(sections)

    def build_dynamic_context(
        self,
        game_session: GameSession,
        chat_history: List[Message],
    ) -> str:
        """
        Build dynamic context that changes every turn.
        This gets injected via assistant prefill.
        """
        sections = []

        # Current state
        state_text = self.state_builder.build(game_session.id)
        if state_text:
            sections.append(f"# CURRENT STATE #\n{state_text}")

        # Retrieved memories
        session = Session.from_json(game_session.session_data)
        session.id = game_session.id
        memories = self.mem_retriever.get_relevant(session, chat_history)
        mem_text = self.mem_retriever.format_for_prompt(memories)
        if mem_text:
            sections.append(mem_text)

        # NPC Context
        npc_context_text = self._build_npc_context(game_session.id)
        if npc_context_text:
            sections.append(npc_context_text)

        return "\n\n".join(sections)

    def _build_npc_context(self, session_id: int) -> str:
        """
        Finds NPCs in the player's location and formats their profiles for context.
        """
        try:
            player = self.db.game_state.get_entity(session_id, "character", "player")
            if not player or "location_key" not in player:
                return ""

            player_location = player["location_key"]
            all_characters = self.db.game_state.get_all_entities_by_type(session_id, "character")

            active_npcs = [
                (key, char) for key, char in all_characters.items()
                if key != "player" and char.get("location_key") == player_location
            ]

            if not active_npcs:
                return ""

            lines = ["# NPC CONTEXT #"]
            for key, char in active_npcs:
                profile_data = self.db.game_state.get_entity(session_id, "npc_profile", key)
                if profile_data:
                    profile = NpcProfile(**profile_data)
                    rel = profile.relationships.get("player")
                    rel_str = f" | Rel(Player): Trust({rel.trust}), Attract({rel.attraction}), Fear({rel.fear})" if rel else ""
                    lines.append(f" - {char.get('name', key)}: Motives({', '.join(profile.motivations)}){rel_str}")
            
            return "\n".join(lines) if len(lines) > 1 else ""
        except Exception as e:
            self.logger.debug(f"Failed to build NPC context: {e}", exc_info=True)
            return ""

    def get_truncated_history(
        self,
        session: Session,
        max_messages: int,
    ) -> List[Message]:
        """Get truncated chat history (user/assistant only, no system messages)."""
        history = session.get_history()  # ✅ Already filtered, no system messages
        if len(history) <= max_messages:
            return history

        # Keep most recent messages
        return history[-max_messages:]
