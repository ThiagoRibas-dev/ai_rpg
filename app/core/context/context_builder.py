import logging
from typing import List
from app.models.game_session import GameSession
from app.models.message import Message
from .state_context import StateContextBuilder
from .memory_retriever import MemoryRetriever
from ..metadata.turn_metadata_service import TurnMetadataService
from .world_info_service import WorldInfoService

class ContextBuilder:
    """Assembles the final system prompt by combining instructions, state, memories, past events, world info, and author's note."""
    def __init__(self, db_manager, vector_store,
                 state_builder: StateContextBuilder,
                 memory_retriever: MemoryRetriever,
                 turnmeta: TurnMetadataService,
                 world_info: WorldInfoService,
                 logger: logging.Logger | None = None):
        self.db = db_manager
        self.vs = vector_store
        self.state_builder = state_builder
        self.mem = memory_retriever
        self.turnmeta = turnmeta
        self.world_info = world_info
        self.logger = logger or logging.getLogger(__name__)

    def get_truncated_history(self, session, max_messages: int) -> List[Message]:
        if not session:
            return []
        full = session.get_history()
        if len(full) <= max_messages:
            return full
        system_prompt = full[0]
        recent = full[-(max_messages - 1):]
        return [system_prompt] + recent

    def _format_turn_metadata_for_context(self, turns: list[dict]) -> str:
        if not turns:
            return ""
        lines = ["# RELEVANT PAST EVENTS #"]
        for t in turns:
            stars = "★" * int(t["importance"])
            tags = f" [{', '.join(t['tags'])}]" if t.get('tags') else ""
            lines.append(f"Turn {t['round_number']} ({stars}){tags}\n   {t['summary']}")
        lines.append("")
        return "\n".join(lines)

    def assemble(self, base_template: str, session: GameSession, history: List[Message]) -> str:
        parts: list[str] = []
        # 1) Instructions
        parts.append(f"### INSTRUCTIONS\n{base_template}\n")
        # 2) Current State
        parts.append(f"### CURRENT STATE\n{self.state_builder.build(session.id)}\n")
        # 3) Memory (manual/persistent)
        if session.memory and session.memory.strip():
            parts.append(f"### MEMORIES\n{session.memory.strip()}\n")
        # 4) Relevant Memories (AI-managed)
        rel_mems = self.mem.get_relevant(session, history, limit=10)
        parts.append(self.mem.format_for_prompt(rel_mems))
        # 5) Relevant Past Events
        if session.id:
            recent_text = " ".join([m.content for m in history[-5:]]) if history else ""
            rel_turns = self.turnmeta.search_relevant_turns(session.id, recent_text, top_k=5, min_importance=3)
            if rel_turns:
                parts.append(self._format_turn_metadata_for_context(rel_turns))
        # 6) World Info (lazy indexed)
        if session.prompt_id:
            self.world_info.ensure_indexed(session.prompt_id)
            wi_texts = self.world_info.search_for_history(session.prompt_id, history, k=4)
            if wi_texts:
                parts.append("### WORLD INFO\n" + "\n\n".join(wi_texts) + "\n")
        # 7) Author's Note
        if session.authors_note and session.authors_note.strip():
            parts.append(f"### AUTHOR'S NOTE\n{session.authors_note.strip()}\n")
        return "\n".join([p for p in parts if p])
