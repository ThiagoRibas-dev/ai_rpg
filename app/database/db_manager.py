import sqlite3
from typing import List, Dict, Optional
from app.models.prompt import Prompt
from app.models.game_session import GameSession
from app.models.world_info import WorldInfo

class DBManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

    def create_tables(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS prompts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    content TEXT NOT NULL
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    session_data TEXT NOT NULL,
                    prompt_id INTEGER NOT NULL,
                    memory TEXT DEFAULT '',
                    authors_note TEXT DEFAULT '',
                    FOREIGN KEY (prompt_id) REFERENCES prompts (id)
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS world_info (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prompt_id INTEGER NOT NULL,
                    keywords TEXT NOT NULL,
                    content TEXT NOT NULL,
                    FOREIGN KEY (prompt_id) REFERENCES prompts (id)
                )
            """)

    # ==================== Prompts ====================
    def create_prompt(self, name: str, content: str) -> Prompt:
        with self.conn:
            cursor = self.conn.execute("INSERT INTO prompts (name, content) VALUES (?, ?)", (name, content))
            return Prompt(id=cursor.lastrowid, name=name, content=content)

    def get_all_prompts(self) -> List[Prompt]:
        with self.conn:
            cursor = self.conn.execute("SELECT id, name, content FROM prompts")
            return [Prompt(**row) for row in cursor.fetchall()]

    def update_prompt(self, prompt: Prompt):
        with self.conn:
            self.conn.execute("UPDATE prompts SET name = ?, content = ? WHERE id = ?", 
                            (prompt.name, prompt.content, prompt.id))

    def delete_prompt(self, prompt_id: int):
        with self.conn:
            self.conn.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))

    # ==================== Sessions ====================
    def save_session(self, name: str, session_data: str, prompt_id: int) -> GameSession:
        with self.conn:
            cursor = self.conn.execute(
                "INSERT INTO sessions (name, session_data, prompt_id, memory, authors_note) VALUES (?, ?, ?, '', '')", 
                (name, session_data, prompt_id)
            )
            return GameSession(
                id=cursor.lastrowid, 
                name=name, 
                session_data=session_data, 
                prompt_id=prompt_id,
                memory="",
                authors_note=""
            )

    def load_session(self, session_id: int) -> GameSession | None:
        with self.conn:
            cursor = self.conn.execute(
                "SELECT id, name, session_data, prompt_id, memory, authors_note FROM sessions WHERE id = ?", 
                (session_id,)
            )
            row = cursor.fetchone()
            if row:
                return GameSession(
                    id=row["id"],
                    name=row["name"],
                    session_data=row["session_data"],
                    prompt_id=row["prompt_id"],
                    memory=row["memory"] or "",
                    authors_note=row["authors_note"] or ""
                )
            return None

    def get_all_sessions(self) -> List[GameSession]:
        with self.conn:
            cursor = self.conn.execute("SELECT id, name, session_data, prompt_id, memory, authors_note FROM sessions")
            return [GameSession(**row) for row in cursor.fetchall()]

    def get_sessions_by_prompt(self, prompt_id: int) -> List[GameSession]:
        with self.conn:
            cursor = self.conn.execute(
                "SELECT id, name, session_data, prompt_id, memory, authors_note FROM sessions WHERE prompt_id = ?", 
                (prompt_id,)
            )
            return [GameSession(**row) for row in cursor.fetchall()]

    def update_session(self, session: GameSession):
        with self.conn:
            self.conn.execute(
                "UPDATE sessions SET name = ?, session_data = ?, prompt_id = ?, memory = ?, authors_note = ? WHERE id = ?",
                (session.name, session.session_data, session.prompt_id, session.memory, session.authors_note, session.id)
            )

    def update_session_context(self, session_id: int, memory: str, authors_note: str):
        """Update only the context fields of a session."""
        with self.conn:
            self.conn.execute(
                "UPDATE sessions SET memory = ?, authors_note = ? WHERE id = ?",
                (memory, authors_note, session_id)
            )

    def get_session_context(self, session_id: int) -> Optional[Dict[str, str]]:
        """Retrieve the context fields for a session."""
        with self.conn:
            cursor = self.conn.execute(
                "SELECT memory, authors_note FROM sessions WHERE id = ?",
                (session_id,)
            )
            row = cursor.fetchone()
            if row:
                return {"memory": row["memory"] or "", "authors_note": row["authors_note"] or ""}
            return None

    # ==================== World Info ====================
    def create_world_info(self, prompt_id: int, keywords: str, content: str) -> WorldInfo:
        with self.conn:
            cursor = self.conn.execute(
                "INSERT INTO world_info (prompt_id, keywords, content) VALUES (?, ?, ?)",
                (prompt_id, keywords, content)
            )
            return WorldInfo(id=cursor.lastrowid, prompt_id=prompt_id, keywords=keywords, content=content)

    def get_world_info_by_prompt(self, prompt_id: int) -> List[WorldInfo]:
        with self.conn:
            cursor = self.conn.execute(
                "SELECT id, prompt_id, keywords, content FROM world_info WHERE prompt_id = ?",
                (prompt_id,)
            )
            return [WorldInfo(**row) for row in cursor.fetchall()]

    def update_world_info(self, world_info: WorldInfo):
        with self.conn:
            self.conn.execute(
                "UPDATE world_info SET keywords = ?, content = ? WHERE id = ?",
                (world_info.keywords, world_info.content, world_info.id)
            )

    def delete_world_info(self, world_info_id: int):
        with self.conn:
            self.conn.execute("DELETE FROM world_info WHERE id = ?", (world_info_id,))