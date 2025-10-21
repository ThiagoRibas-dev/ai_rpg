import sqlite3
from typing import List
from app.models.prompt import Prompt
from app.models.game_session import GameSession

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
                    FOREIGN KEY (prompt_id) REFERENCES prompts (id)
                )
            """)

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
            self.conn.execute("UPDATE prompts SET name = ?, content = ? WHERE id = ?", (prompt.name, prompt.content, prompt.id))

    def delete_prompt(self, prompt_id: int):
        with self.conn:
            self.conn.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))

    def save_session(self, name: str, session_data: str, prompt_id: int) -> GameSession:
        with self.conn:
            cursor = self.conn.execute("INSERT INTO sessions (name, session_data, prompt_id) VALUES (?, ?, ?)", (name, session_data, prompt_id))
            return GameSession(id=cursor.lastrowid, name=name, session_data=session_data, prompt_id=prompt_id)

    def load_session(self, session_id: int) -> GameSession | None:
        with self.conn:
            cursor = self.conn.execute("SELECT id, name, session_data, prompt_id FROM sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            return GameSession(**row) if row else None

    def get_all_sessions(self) -> List[GameSession]:
        with self.conn:
            cursor = self.conn.execute("SELECT id, name, session_data, prompt_id FROM sessions")
            return [GameSession(**row) for row in cursor.fetchall()]

    def get_sessions_by_prompt(self, prompt_id: int) -> List[GameSession]:
        with self.conn:
            cursor = self.conn.execute("SELECT id, name, session_data, prompt_id FROM sessions WHERE prompt_id = ?", (prompt_id,))
            return [GameSession(**row) for row in cursor.fetchall()]

    def update_session(self, session: GameSession):
        with self.conn:
            self.conn.execute("UPDATE sessions SET name = ?, session_data = ?, prompt_id = ? WHERE id = ?",
                              (session.name, session.session_data, session.prompt_id, session.id))
