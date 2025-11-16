"""Repository for world info operations."""

from typing import List
from app.models.world_info import WorldInfo
from .base_repository import BaseRepository


class WorldInfoRepository(BaseRepository):
    """Handles all world info related database operations."""

    def create_table(self):
        """Creates the world_info table."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS world_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_id INTEGER NOT NULL,
                keywords TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (prompt_id) REFERENCES prompts (id) ON DELETE CASCADE
            );
            """
        )
        self.conn.commit()

    def create(self, prompt_id: int, keywords: str, content: str) -> WorldInfo:
        """Create a new world info entry."""
        cursor = self._execute(
            "INSERT INTO world_info (prompt_id, keywords, content) VALUES (?, ?, ?)",
            (prompt_id, keywords, content),
        )
        self._commit()
        world_info_id = cursor.lastrowid
        if world_info_id is None:
            raise ValueError("Failed to retrieve world info ID after insertion.")
        return WorldInfo(
            id=world_info_id, prompt_id=prompt_id, keywords=keywords, content=content
        )

    def get_by_prompt(self, prompt_id: int) -> List[WorldInfo]:
        """Get all world info entries for a prompt."""
        rows = self._fetchall(
            "SELECT id, prompt_id, keywords, content FROM world_info WHERE prompt_id = ?",
            (prompt_id,),
        )
        return [WorldInfo(**dict(row)) for row in rows]

    def update(self, world_info: WorldInfo):
        """Update a world info entry."""
        self._execute(
            "UPDATE world_info SET keywords = ?, content = ? WHERE id = ?",
            (world_info.keywords, world_info.content, world_info.id),
        )
        self._commit()

    def delete(self, world_info_id: int):
        """Delete a world info entry."""
        self._execute("DELETE FROM world_info WHERE id = ?", (world_info_id,))
        self._commit()
