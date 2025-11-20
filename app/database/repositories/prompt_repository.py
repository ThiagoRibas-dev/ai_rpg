"""Repository for prompt operations."""

from typing import List
from app.models.prompt import Prompt
from .base_repository import BaseRepository


class PromptRepository(BaseRepository):
    """Handles all prompt-related database operations."""

    def create_table(self):
        """Creates the prompts table."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                content TEXT NOT NULL,
                rules_document TEXT DEFAULT '',
                template_manifest TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        self.conn.commit()

    def create(
        self,
        name: str,
        content: str,
        rules_document: str = "",
        template_manifest: str = "{}",
    ) -> Prompt:
        """Create a new prompt."""
        cursor = self._execute(
            "INSERT INTO prompts (name, content, rules_document, template_manifest) VALUES (?, ?, ?, ?)",
            (name, content, rules_document, template_manifest),
        )
        self._commit()
        return Prompt(
            id=cursor.lastrowid,
            name=name,
            content=content,
            rules_document=rules_document,
            template_manifest=template_manifest,
        )

    def get_all(self) -> List[Prompt]:
        """Get all prompts."""
        rows = self._fetchall(
            "SELECT id, name, content, rules_document, template_manifest FROM prompts"
        )
        return [Prompt(**dict(row)) for row in rows]

    def get_by_id(self, prompt_id: int) -> Prompt | None:
        """Get a prompt by ID."""
        row = self._fetchone(
            "SELECT id, name, content, rules_document, template_manifest FROM prompts WHERE id = ?",
            (prompt_id,),
        )
        return Prompt(**dict(row)) if row else None

    def update(self, prompt: Prompt):
        """Update a prompt."""
        self._execute(
            "UPDATE prompts SET name = ?, content = ?, rules_document = ?, template_manifest = ? WHERE id = ?",
            (
                prompt.name,
                prompt.content,
                prompt.rules_document,
                prompt.template_manifest,
                prompt.id,
            ),
        )
        self._commit()

    def delete(self, prompt_id: int):
        """Delete a prompt."""
        self._execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
        self._commit()
