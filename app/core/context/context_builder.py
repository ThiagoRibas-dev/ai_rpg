import logging
import json
from typing import List
from app.models.session import Session
from app.models.game_session import GameSession
from app.models.message import Message
from app.core.llm.prompts import SESSION_ZERO_TEMPLATE

class ContextBuilder:
    """Builds static and dynamic prompt components for caching optimization."""
    
    def __init__(self, db_manager, vector_store, state_builder, mem_retriever, 
                 turnmeta, world_info, logger: logging.Logger | None = None):
        self.db = db_manager
        self.vs = vector_store
        self.state_builder = state_builder
        self.mem_retriever = mem_retriever
        self.turnmeta = turnmeta
        self.world_info = world_info
        self.logger = logger or logging.getLogger(__name__)

    def build_static_system_instruction(self, game_session: GameSession, 
                                    tool_schemas: List[dict]) -> str:
        """
        Build the cacheable system instruction.
        Call this when:
        - Session starts
        - Game mode changes (SETUP → GAMEPLAY)
        - Author's note is edited
        - Tool availability changes
        """
        sections = []
        
        # 1. User's game prompt (from Session.system_prompt, NOT history)
        session_data = Session.from_json(game_session.session_data)
        user_game_prompt = session_data.get_system_prompt()
        sections.append(user_game_prompt)
        
        # 2. Tool schemas (only if tools are available)
        if tool_schemas:
            sections.append("# AVAILABLE TOOLS #")
            sections.append(json.dumps(tool_schemas, indent=2))
        
        # 3. Author's note (if exists)
        if game_session.authors_note:
            sections.append("# NOTE #")
            sections.append(game_session.authors_note)
        
        return "\n\n".join(sections)

    def build_dynamic_context(self, game_session: GameSession, 
                             chat_history: List[Message]) -> str:
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
        
        # World info
        wi_entries = self.world_info.search_for_history(game_session.prompt_id, chat_history)
        if wi_entries:
            sections.append("# WORLD INFO #\n" + "\n".join(wi_entries))
        
        return "\n\n".join(sections)

    def get_truncated_history(self, session: Session, max_messages: int) -> List[Message]:
        """Get truncated chat history (user/assistant only, no system messages)."""
        history = session.get_history()  # ✅ Already filtered, no system messages
        
        if len(history) <= max_messages:
            return history
        
        # Keep most recent messages
        return history[-max_messages:]

    def get_session_zero_prompt_template(self) -> str:
        """Returns the Session Zero system prompt template."""
        return SESSION_ZERO_TEMPLATE
