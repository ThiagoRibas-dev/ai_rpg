import sqlite3
from typing import List, Dict, Optional, Any
from app.models.prompt import Prompt
from app.models.game_session import GameSession
from app.models.world_info import WorldInfo
from app.models.memory import Memory
from app.database.repositories import (
    PromptRepository,
    SessionRepository,
    MemoryRepository,
    GameStateRepository,
    WorldInfoRepository,
    TurnMetadataRepository,
    SchemaExtensionRepository,
)


class DBManager:
    """
    Database connection manager with repository-based access.

    Usage:
        with DBManager("ai_rpg.db") as db:
            prompt = db.prompts.create("My Prompt", "Content")
            all_prompts = db.prompts.get_all()
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None

        # Repositories (initialized in __enter__)
        self.prompts: Optional[PromptRepository] = None
        self.sessions: Optional[SessionRepository] = None
        self.memories: Optional[MemoryRepository] = None
        self.game_state: Optional[GameStateRepository] = None
        self.world_info: Optional[WorldInfoRepository] = None
        self.turn_metadata: Optional[TurnMetadataRepository] = None
        self.schema_extensions: Optional[SchemaExtensionRepository] = None

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

        # Initialize all repositories
        self.prompts = PromptRepository(self.conn)
        self.sessions = SessionRepository(self.conn)
        self.memories = MemoryRepository(self.conn)
        self.game_state = GameStateRepository(self.conn)
        self.world_info = WorldInfoRepository(self.conn)
        self.turn_metadata = TurnMetadataRepository(self.conn)
        self.schema_extensions = SchemaExtensionRepository(self.conn)

        # Assert that repositories are not None for Mypy
        assert self.prompts is not None
        assert self.sessions is not None
        assert self.memories is not None
        assert self.game_state is not None
        assert self.world_info is not None
        assert self.turn_metadata is not None
        assert self.schema_extensions is not None

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

    def create_tables(self):
        """Initialize all database tables."""
        with self.conn:
            self._create_prompts_table()
            self._create_sessions_table()
            self._create_world_info_table()
            self._create_memories_table()
            self._create_turn_metadata_table()
            self._create_schema_extensions_table()
            self._create_game_state_table()
            self._create_indexes()

    # ✅ BACKWARD COMPATIBILITY: Delegate to repositories
    # These methods maintain the old API for existing code

    # Prompts
    def create_prompt(
        self,
        name: str,
        content: str,
        initial_message: str = "",
        rules_document: str = "",
        template_manifest: str = "{}",
    ) -> Prompt:
        with self.conn:
            return self.prompts.create(
                name, content, initial_message, rules_document, template_manifest
            )

    def get_all_prompts(self) -> List[Prompt]:
        with self.conn:
            return self.prompts.get_all()

    def update_prompt(self, prompt: Prompt):
        with self.conn:
            self.prompts.update(prompt)

    def delete_prompt(self, prompt_id: int):
        with self.conn:
            self.prompts.delete(prompt_id)

    # Sessions
    def save_session(
        self, name: str, session_data: str, prompt_id: int, setup_phase_data: str = "{}"
    ) -> GameSession:
        with self.conn:
            return self.sessions.create(name, session_data, prompt_id, setup_phase_data)

    def load_session(self, session_id: int) -> GameSession | None:
        with self.conn:
            return self.sessions.get_by_id(session_id)

    def get_all_sessions(self) -> List[GameSession]:
        with self.conn:
            return self.sessions.get_all()

    def get_sessions_by_prompt(self, prompt_id: int) -> List[GameSession]:
        with self.conn:
            return self.sessions.get_by_prompt(prompt_id)

    def update_session(self, session: GameSession):
        with self.conn:
            self.sessions.update(session)

    def update_session_context(self, session_id: int, memory: str, authors_note: str):
        with self.conn:
            self.sessions.update_context(session_id, memory, authors_note)

    def update_session_game_time(self, session_id: int, game_time: str):
        with self.conn:
            self.sessions.update_game_time(session_id, game_time)

    def get_session_context(self, session_id: int) -> Optional[dict]:
        with self.conn:
            return self.sessions.get_context(session_id)

    # World Info
    def create_world_info(
        self, prompt_id: int, keywords: str, content: str
    ) -> WorldInfo:
        with self.conn:
            return self.world_info.create(prompt_id, keywords, content)

    def get_world_info_by_prompt(self, prompt_id: int) -> List[WorldInfo]:
        with self.conn:
            return self.world_info.get_by_prompt(prompt_id)

    def update_world_info(self, world_info: WorldInfo):
        with self.conn:
            self.world_info.update(world_info)

    def delete_world_info(self, world_info_id: int):
        with self.conn:
            self.world_info.delete(world_info_id)

    # Memories
    def create_memory(
        self,
        session_id: int,
        kind: str,
        content: str,
        priority: int = 3,
        tags: List[str] | None = None,
        fictional_time: str | None = None,
    ) -> Memory:
        with self.conn:
            return self.memories.create(
                session_id, kind, content, priority, tags, fictional_time
            )

    def get_memories_by_session(self, session_id: int) -> List[Memory]:
        with self.conn:
            return self.memories.get_by_session(session_id)

    def query_memories(
        self,
        session_id: int,
        kind: str | None = None,
        tags: List[str] | None = None,
        query_text: str | None = None,
        limit: int = 10,
    ) -> List[Memory]:
        with self.conn:
            return self.memories.query(session_id, kind, tags, query_text, limit)

    def update_memory_access(self, memory_id: int):
        with self.conn:
            self.memories.update_access(memory_id)

    def update_memory(
        self,
        memory_id: int,
        kind: str | None = None,
        content: str | None = None,
        priority: int | None = None,
        tags: List[str] | None = None,
    ) -> Optional[Memory]:
        with self.conn:
            return self.memories.update(memory_id, kind, content, priority, tags)

    def get_memory_by_id(self, memory_id: int) -> Optional[Memory]:
        with self.conn:
            return self.memories.get_by_id(memory_id)

    def delete_memory(self, memory_id: int):
        with self.conn:
            self.memories.delete(memory_id)

    def get_memory_statistics(self, session_id: int) -> Dict[str, Any]:
        with self.conn:
            return self.memories.get_statistics(session_id)

    # Game State
    def get_game_state_entity(
        self, session_id: int, entity_type: str, entity_key: str
    ) -> dict:
        with self.conn:
            return self.game_state.get_entity(session_id, entity_type, entity_key)

    def set_game_state_entity(
        self, session_id: int, entity_type: str, entity_key: str, state_data: dict
    ) -> int:
        with self.conn:
            return self.game_state.set_entity(
                session_id, entity_type, entity_key, state_data
            )

    def get_all_entities_by_type(self, session_id: int, entity_type: str) -> dict:
        with self.conn:
            return self.game_state.get_all_entities_by_type(session_id, entity_type)

    def delete_game_state_entity(
        self, session_id: int, entity_type: str, entity_key: str
    ):
        with self.conn:
            self.game_state.delete_entity(session_id, entity_type, entity_key)

    def get_all_game_state(self, session_id: int) -> dict:
        with self.conn:
            return self.game_state.get_all(session_id)

    def get_game_state_statistics(self, session_id: int) -> dict:
        with self.conn:
            return self.game_state.get_statistics(session_id)

    def clear_game_state(self, session_id: int):
        with self.conn:
            self.game_state.clear(session_id)

    # Schema Extensions
    def create_schema_extension(
        self,
        session_id: int,
        entity_type: str,
        property_name: str,
        definition_dict: Dict[str, Any],
    ):
        with self.conn:
            self.schema_extensions.create(
                session_id, entity_type, property_name, definition_dict
            )

    def get_schema_extensions(
        self, session_id: int, entity_type: str
    ) -> Dict[str, Dict[str, Any]]:
        with self.conn:
            return self.schema_extensions.get_by_entity_type(session_id, entity_type)

    def delete_schema_extension(
        self, session_id: int, entity_type: str, property_name: str
    ):
        with self.conn:
            self.schema_extensions.delete(session_id, entity_type, property_name)

    def get_all_schema_extensions(
        self, session_id: int
    ) -> Dict[str, Dict[str, Dict[str, Any]]]:
        with self.conn:
            return self.schema_extensions.get_all(session_id)

    # Turn Metadata
    def create_turn_metadata(
        self,
        session_id: int,
        prompt_id: int,
        round_number: int,
        summary: str,
        tags: List[str],
        importance: int,
    ) -> int:
        with self.conn:
            return self.turn_metadata.create(
                session_id, prompt_id, round_number, summary, tags, importance
            )

    def get_turn_metadata_range(
        self, session_id: int, start_round: int, end_round: int
    ) -> List[Dict[str, Any]]:
        with self.conn:
            return self.turn_metadata.get_range(session_id, start_round, end_round)

    def get_all_turn_metadata(self, session_id: int) -> List[Dict[str, Any]]:
        with self.conn:
            return self.turn_metadata.get_all(session_id)

    # Private table creation methods
    def _create_prompts_table(self):
        self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS prompts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        content TEXT NOT NULL,
                        initial_message TEXT DEFAULT '',
                        rules_document TEXT DEFAULT '',
                        template_manifest TEXT DEFAULT '{}'
                    )        """)

    def _create_sessions_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                session_data TEXT NOT NULL,
                prompt_id INTEGER NOT NULL,
                memory TEXT DEFAULT '',
                authors_note TEXT DEFAULT '',
                game_time TEXT DEFAULT 'Day 1, Dawn',
                game_mode TEXT DEFAULT 'SETUP',
                setup_phase_data TEXT DEFAULT '{}',
                FOREIGN KEY (prompt_id) REFERENCES prompts (id)
            )
        """)

    def _create_world_info_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS world_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_id INTEGER NOT NULL,
                keywords TEXT NOT NULL,
                content TEXT NOT NULL,
                FOREIGN KEY (prompt_id) REFERENCES prompts (id)
            )
        """)

    def _create_memories_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                kind TEXT NOT NULL,
                content TEXT NOT NULL,
                priority INTEGER NOT NULL DEFAULT 3,
                tags TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fictional_time TEXT DEFAULT NULL,
                last_accessed TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
            )
        """)

    def _create_turn_metadata_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS turn_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                prompt_id INTEGER NOT NULL,
                round_number INTEGER NOT NULL,
                summary TEXT NOT NULL,
                tags TEXT DEFAULT '[]',
                importance INTEGER DEFAULT 3,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE,
                FOREIGN KEY (prompt_id) REFERENCES prompts (id)
            )
        """)

    def _create_schema_extensions_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_extensions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                entity_type TEXT NOT NULL,
                property_name TEXT NOT NULL,
                definition TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE,
                UNIQUE(session_id, entity_type, property_name)
            )
        """)

    def _create_game_state_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS game_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                entity_type TEXT NOT NULL,
                entity_key TEXT NOT NULL,
                state_data TEXT NOT NULL,
                version INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE,
                UNIQUE(session_id, entity_type, entity_key)
            )
        """)

    def _create_indexes(self):
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_schema_extensions ON schema_extensions(session_id, entity_type)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_turn_metadata_session 
            ON turn_metadata(session_id)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_turn_metadata_importance 
            ON turn_metadata(importance)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_session 
            ON memories(session_id)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_kind 
            ON memories(kind)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_priority 
            ON memories(priority)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_game_state_session 
            ON game_state(session_id)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_game_state_entity_type 
            ON game_state(entity_type)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_game_state_lookup 
            ON game_state(session_id, entity_type, entity_key)
        """)
