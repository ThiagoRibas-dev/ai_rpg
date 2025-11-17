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

        # Determine active NPCs in the scene for contextual retrieval
        active_npc_keys = self._get_active_npc_keys(game_session.id)

        # Retrieved memories
        session = Session.from_json(game_session.session_data)
        session.id = game_session.id

        # Pass active NPCs to the retriever for contextual prioritization
        memories = self.mem_retriever.get_relevant(
            session,
            chat_history,
            active_npc_keys=active_npc_keys
        )
        mem_text = self.mem_retriever.format_for_prompt(memories)
        if mem_text:
            sections.append(mem_text)

        # NPC context
        npc_context_text = self._build_npc_context(game_session.id)
        if npc_context_text:
            sections.append(npc_context_text)

        return "\n\n".join(sections)
    
    def _get_active_scene_members(self, session_id: int) -> List[str]:
        """Helper to get a list of character keys from the active scene."""
        try:
            scene = self.db.game_state.get_entity(session_id, "scene", "active_scene")
            if not scene or "members" not in scene:
                return []
            
            members = scene.get("members", [])
            # Parse 'character:key' format
            char_keys = [
                member.split(":", 1)[1] for member in members
                if member.startswith("character:")
            ]
            return char_keys
        except Exception as e:
            self.logger.debug(f"Could not retrieve active scene members: {e}", exc_info=True)
            return []

    def _get_active_npc_keys(self, session_id: int) -> List[str]:
        """Finds the entity keys of NPCs in the active scene."""
        all_members = self._get_active_scene_members(session_id)
        return [key for key in all_members if key != "player"]


    def _build_npc_context(self, session_id: int) -> str:
        """
        Finds NPCs in the active scene and formats their profiles for context.
        """
        active_npc_keys = self._get_active_npc_keys(session_id)
        if not active_npc_keys:
            return ""
        
        lines = ["# NPC CONTEXT #"]
        for key in active_npc_keys:
            try:
                char = self.db.game_state.get_entity(session_id, "character", key)
                profile_data = self.db.game_state.get_entity(session_id, "npc_profile", key)
                if char and profile_data:
                    profile = NpcProfile(**profile_data)
                    rel = profile.relationships.get("player")
                    rel_str = f" | Rel(Player): Trust({rel.trust}), Attract({rel.attraction}), Fear({rel.fear})" if rel else ""
                    lines.append(f" - {char.get('name', key)}: Motives({', '.join(profile.motivations)}){rel_str}")
            except Exception as e:
                self.logger.debug(f"Failed to build context for NPC '{key}': {e}", exc_info=True)
                continue
        
        return "\n".join(lines) if len(lines) > 1 else ""

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
