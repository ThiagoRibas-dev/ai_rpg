import sqlite3

from app.database.repositories import (
    GameStateRepository,
    ManifestRepository,
    MemoryRepository,
    PromptRepository,
    RulesetRepository,
    SessionRepository,
    StatTemplateRepository,
    TurnMetadataRepository,
)


class DBManager:
    """
    Database connection manager with repository-based access.

    Usage:
        with DBManager("ai_rpg.db") as db:
            manifest = db.manifests.get_by_system_id("dnd_5e")
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None

        # Repositories (initialized in __enter__)
        self.prompts: PromptRepository | None = None
        self.sessions: SessionRepository | None = None
        self.memories: MemoryRepository | None = None
        self.game_state: GameStateRepository | None = None
        self.turn_metadata: TurnMetadataRepository | None = None
        self.rulesets: RulesetRepository | None = None
        self.stat_templates: StatTemplateRepository | None = None
        self.manifests: ManifestRepository | None = None

    def __enter__(self):
        # Set a long timeout (30s) so threads wait rather than crashing immediately
        # Set isolation_level=None to enable autocommit mode.
        self.conn = sqlite3.connect(self.db_path, timeout=30.0, isolation_level=None)

        # Enable Write-Ahead Logging (WAL).
        self.conn.execute("PRAGMA journal_mode=WAL;")

        # Enforce foreign keys
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
        self.manifests = ManifestRepository(self.conn)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

    def create_tables(self):
        """Initialize all database tables."""
        if not self.conn:
            with self as db:
                db._create_all_tables_and_indexes()
        else:
            self._create_all_tables_and_indexes()

    def _create_all_tables_and_indexes(self):
        """
        Internal method to create all tables by delegating to repositories,
        then create all indexes.
        """
        repositories = [
            self.prompts,
            self.sessions,
            self.memories,
            self.turn_metadata,
            self.game_state,
            self.rulesets,
            self.stat_templates,
            self.manifests,
        ]

        for repo in repositories:
            if repo:
                repo.create_table()

        self._create_indexes()

    def _create_indexes(self):
        """Create all database indexes."""
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
