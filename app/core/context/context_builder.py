import logging
from typing import List
from app.models.game_session import GameSession
from app.models.message import Message
from app.models.property_definition import PropertyDefinition # Import PropertyDefinition
from app.core.llm.prompts import SESSION_ZERO_TEMPLATE # Import the new template
from .state_context import StateContextBuilder
from .memory_retriever import MemoryRetriever
from app.core.metadata.turn_metadata_service import TurnMetadataService # Changed to absolute import
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

    def get_session_zero_prompt_template(self) -> str:
        """Returns the system prompt template for Session Zero."""
        return SESSION_ZERO_TEMPLATE

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

    def _get_formatted_custom_rules(self, session_id: int) -> str:
        """
        Retrieves and formats custom property definitions for injection into the system prompt.
        """
        if not session_id:
            return ""
        
        schema_extensions = self.db.get_all_schema_extensions(session_id)
        if not schema_extensions:
            return ""
        
        lines = ["# CUSTOM GAME MECHANICS", ""]
        for entity_type, properties in schema_extensions.items():
            if not properties:
                continue
            
            lines.append(f"## {entity_type.title()}")
            for prop_name, prop_def_dict in properties.items():
                try:
                    prop_def = PropertyDefinition(**prop_def_dict) # Validate with Pydantic model
                except Exception as e:
                    self.logger.error(f"Invalid PropertyDefinition for {prop_name}: {e}")
                    continue

                icon = prop_def.icon if prop_def.icon else ""
                desc = prop_def.description if prop_def.description else ""
                
                range_str = ""
                if prop_def.has_max and prop_def.max_value is not None:
                    range_str = f"(0-{prop_def.max_value})"
                elif prop_def.min_value is not None or prop_def.max_value is not None:
                    min_v = prop_def.min_value if prop_def.min_value is not None else "?"
                    max_v = prop_def.max_value if prop_def.max_value is not None else "?"
                    range_str = f"({min_v} to {max_v})"
                elif prop_def.type == "enum" and prop_def.allowed_values:
                    range_str = f"({', '.join(prop_def.allowed_values)})"
                
                regenerates_str = " (Regenerates)" if prop_def.regenerates else ""
                
                lines.append(f"- **{icon} {prop_name}** {range_str}: {desc}{regenerates_str}")
            
            lines.append("")
        
        return "\n".join(lines)

    def assemble(self, base_template: str, session: GameSession, history: List[Message]) -> str:
        parts: list[str] = []
        
        # Inject custom rules FIRST (high priority) if in GAMEPLAY mode
        if session.id and session.game_mode == "GAMEPLAY":
            custom_rules = self._get_formatted_custom_rules(session.id)
            if custom_rules:
                parts.append(custom_rules)
        
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
