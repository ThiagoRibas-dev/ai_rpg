"""Repository for turn metadata operations."""

import json
from typing import Any, Dict, List
from .base_repository import BaseRepository


class TurnMetadataRepository(BaseRepository):
    """Handles all turn metadata related database operations."""

    def create_table(self):
        """Creates the turn_metadata table."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS turn_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                prompt_id INTEGER NOT NULL,
                round_number INTEGER NOT NULL,
                summary TEXT NOT NULL,
                tags TEXT NOT NULL,
                importance INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE,
                FOREIGN KEY (prompt_id) REFERENCES prompts (id) ON DELETE CASCADE
            );
            """
        )
        self.conn.commit()

    def create(
        self,
        session_id: int,
        prompt_id: int,
        round_number: int,
        summary: str,
        tags: List[str],
        importance: int,
    ) -> int:
        """Create a turn metadata entry and return its ID."""
        tags_json = json.dumps(tags)

        cursor = self._execute(
            """INSERT INTO turn_metadata 
            (session_id, prompt_id, round_number, summary, tags, importance) 
            VALUES (?, ?, ?, ?, ?, ?)""",
            (session_id, prompt_id, round_number, summary, tags_json, importance),
        )
        self._commit()
        turn_id = cursor.lastrowid
        if turn_id is None:
            raise ValueError("Failed to retrieve turn metadata ID after insertion.")
        return turn_id

    def get_range(
        self, session_id: int, start_round: int, end_round: int
    ) -> List[Dict[str, Any]]:
        """Get metadata for a range of rounds."""
        rows = self._fetchall(
            """SELECT round_number, summary, tags, importance 
            FROM turn_metadata 
            WHERE session_id = ? AND round_number BETWEEN ? AND ?
            ORDER BY round_number ASC""",
            (session_id, start_round, end_round),
        )
        results = []
        for row in rows:
            results.append(
                {
                    "round_number": row["round_number"],
                    "summary": row["summary"],
                    "tags": json.loads(row["tags"]),
                    "importance": row["importance"],
                }
            )
        return results

    def get_all(self, session_id: int) -> List[Dict[str, Any]]:
        """Get all metadata for a session."""
        rows = self._fetchall(
            """SELECT round_number, summary, tags, importance 
            FROM turn_metadata 
            WHERE session_id = ?
            ORDER BY round_number ASC""",
            (session_id,),
        )
        results = []
        for row in rows:
            results.append(
                {
                    "round_number": row["round_number"],
                    "summary": row["summary"],
                    "tags": json.loads(row["tags"]),
                    "importance": row["importance"],
                }
            )
        return results
