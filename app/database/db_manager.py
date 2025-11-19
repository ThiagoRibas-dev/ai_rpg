import sqlite3
from typing import Optional
from app.database.repositories import (
    PromptRepository,
    SessionRepository,
    MemoryRepository,
    GameStateRepository,
    TurnMetadataRepository,
    RulesetRepository,
    StatTemplateRepository,
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
        self.turn_metadata: Optional[TurnMetadataRepository] = None
        self.rulesets: Optional[RulesetRepository] = None
        self.stat_templates: Optional[StatTemplateRepository] = None

    def __enter__(self):
        # Set a long timeout (30s) so threads wait rather than crashing immediately
        # Set isolation_level=None to enable autocommit mode. 
        # This prevents python's sqlite3 from implicitly holding transactions open, which causes locking issues in threaded apps.
        self.conn = sqlite3.connect(self.db_path, timeout=30.0, isolation_level=None)
        
        # Enable Write-Ahead Logging (WAL). 
        # This allows simultaneous readers and writers, drastically reducing locks.
        self.conn.execute("PRAGMA journal_mode=WAL;")
        
        # Enforce foreign keys (SQLite defaults to off)
        self.conn.execute("PRAGMA foreign_keys=ON;")
        
        self.conn.row_factory = sqlite3.Row

        # Initialize all repositories
        self.prompts = PromptRepository(self.conn)
        self.sessions = SessionRepository(self.conn)
        self.memories = MemoryRepository(self.conn)
        self.game_state = GameStateRepository(self.conn)
        self.turn_metadata = TurnMetadataRepository(self.conn)
        self.rulesets = RulesetRepository(self.conn)
        self.stat_templates = StatTemplateRepository(self.conn)

        # Assert that repositories are not None for Mypy
        assert self.prompts is not None
        assert self.sessions is not None
        assert self.memories is not None
        assert self.game_state is not None
        assert self.turn_metadata is not None
        assert self.rulesets is not None
        assert self.stat_templates is not None

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

    def create_tables(self):
        """Initialize all database tables."""
        if not self.conn:
            # Allow creating tables even outside a 'with' block for setup scripts
            with self as db:
                db._create_all_tables_and_indexes()
        else:
            self._create_all_tables_and_indexes()

    def _create_all_tables_and_indexes(self):
        """
        Internal method to create all tables by delegating to repositories,
        then create all indexes.
        """
        # COMMENT: This is the core change. We create a list of all repository
        # instances that are initialized in the __enter__ method.
        repositories = [
            self.prompts,
            self.sessions,
            self.memories,
            self.turn_metadata,
            self.game_state,
            self.rulesets,
            self.stat_templates,
        ]

        # COMMENT: We loop through the list and call the new `create_table()`
        # method on each one. This makes the DBManager incredibly flexible.
        # Adding a new table in the future just means adding a new repository
        # to the list above.
        for repo in repositories:
            if repo: # Mypy check
                repo.create_table()

        # COMMENT: After all tables are created, we call a dedicated method
        # to create the indexes, which often depend on multiple tables existing.
        self._create_indexes()

    def _create_indexes(self):
        """Create all database indexes."""
        # COMMENT: This new method centralizes all index creation logic. It's
        # cleaner than having index statements scattered in different places.
        cursor = self.conn.cursor()
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_session_id ON memories(session_id);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_kind ON memories(kind);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_turn_metadata_session_id ON turn_metadata(session_id);"
        )
        self.conn.commit()
