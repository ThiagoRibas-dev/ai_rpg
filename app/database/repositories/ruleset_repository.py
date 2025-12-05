
"""Repository for Ruleset operations."""

from typing import List, Optional
from .base_repository import BaseRepository
from app.models.ruleset import Ruleset


class RulesetRepository(BaseRepository):
    """Handles database operations for game Rulesets (static system definitions)."""

    def create_table(self):
        """Creates the rulesets table."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS rulesets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                data_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        self.conn.commit()

    def create(self, ruleset: Ruleset) -> int:
        """
        Save a new Ruleset to the database. Returns the new ID.
        """
        data_str = ruleset.model_dump_json()
        name = ruleset.meta.get("name", "Untitled Ruleset") if ruleset.meta else "Untitled Ruleset"

        cursor = self._execute(
            """INSERT INTO rulesets (name, data_json) 
               VALUES (?, ?)""",
            (name, data_str),
        )
        self._commit()
        
        if cursor.lastrowid:
            return cursor.lastrowid
        raise ValueError("Failed to create ruleset")

    def get_by_id(self, ruleset_id: int) -> Optional[Ruleset]:
        """Retrieve a Ruleset by ID."""
        row = self._fetchone(
            "SELECT data_json FROM rulesets WHERE id = ?", (ruleset_id,)
        )
        if row:
            try:
                return Ruleset.model_validate_json(row["data_json"])
            except Exception:
                return None
        return None

    def get_by_name(self, name: str) -> Optional[dict]:
        """Retrieve a Ruleset ID and Data by Name."""
        row = self._fetchone(
            "SELECT id, data_json FROM rulesets WHERE name = ?", (name,)
        )
        if row:
            return {"id": row["id"], "data_json": row["data_json"]}
        return None

    def get_all(self) -> List[dict]:
        """
        Get all rulesets (metadata only).
        Returns a list of dicts {'id': int, 'name': str}.
        """
        rows = self._fetchall("SELECT id, name FROM rulesets ORDER BY name")
        return [{"id": row["id"], "name": row["name"]} for row in rows]

    def update(self, ruleset_id: int, ruleset: Ruleset):
        """Update an existing ruleset."""
        data_str = ruleset.model_dump_json()
        name = ruleset.meta.get("name", "Untitled Ruleset")
        
        self._execute(
            "UPDATE rulesets SET name = ?, data_json = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (name, data_str, ruleset_id),
        )
        self._commit()

    def delete(self, ruleset_id: int):
        """Delete a ruleset."""
        self._execute("DELETE FROM rulesets WHERE id = ?", (ruleset_id,))
        self._commit()
