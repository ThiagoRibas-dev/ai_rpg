"""Repository for StatBlockTemplate operations."""

from typing import List, Optional, Any
from .base_repository import BaseRepository
from pydantic import BaseModel
# We import both for backward compatibility check if needed, 
# but mostly we rely on model_dump_json
from app.models.stat_block import StatBlockTemplate
from app.models.sheet_schema import CharacterSheetSpec

class StatTemplateRepository(BaseRepository):
    """
    Handles database operations for Entity Templates (StatBlocks or SheetSpecs).
    These define the 'shape' of a character sheet.
    """

    def create_table(self):
        """Creates the stat_templates table."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS stat_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ruleset_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                data_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ruleset_id) REFERENCES rulesets (id) ON DELETE CASCADE
            );
            """
        )
        self.conn.commit()

    def create(self, ruleset_id: int, template: BaseModel) -> int:
        """
        Save a new Template. Returns the new ID.
        Accepts either StatBlockTemplate (Old) or CharacterSheetSpec (New).
        """
        data_str = template.model_dump_json()
        
        # Determine name
        name = "Untitled Template"
        if hasattr(template, "template_name"):
            name = template.template_name
        elif hasattr(template, "meta") and hasattr(template.meta, "fields"):
            # Try to find a system name in meta fields of new spec
            # Fallback to generic
            pass

        cursor = self._execute(
            """INSERT INTO stat_templates (ruleset_id, name, data_json) 
               VALUES (?, ?, ?)""",
            (ruleset_id, name, data_str),
        )
        self._commit()
        if cursor.lastrowid:
            return cursor.lastrowid
        raise ValueError("Failed to create stat template")

    def get_by_id(self, template_id: int) -> Optional[Any]:
        """Retrieve a template by ID. Tries New Spec first, then Old."""
        row = self._fetchone(
            "SELECT data_json FROM stat_templates WHERE id = ?", (template_id,)
        )
        if row:
            json_data = row["data_json"]
            # Try parsing as New Spec
            try:
                return CharacterSheetSpec.model_validate_json(json_data)
            except Exception:
                pass
            
            # Try parsing as Old Spec
            try:
                return StatBlockTemplate.model_validate_json(json_data)
            except Exception:
                return None
        return None

    def get_by_ruleset(self, ruleset_id: int) -> List[dict]:
        """
        Get all templates for a specific ruleset.
        Returns list of {'id': int, 'name': str}.
        """
        rows = self._fetchall(
            "SELECT id, name FROM stat_templates WHERE ruleset_id = ? ORDER BY name",
            (ruleset_id,),
        )
        return [{"id": row["id"], "name": row["name"]} for row in rows]

    def update(self, template_id: int, template: BaseModel):
        """Update an existing template."""
        data_str = template.model_dump_json()
        name = "Updated Template"
        if hasattr(template, "template_name"):
            name = template.template_name

        self._execute(
            """UPDATE stat_templates 
               SET name = ?, data_json = ?, updated_at = CURRENT_TIMESTAMP 
               WHERE id = ?""",
            (name, data_str, template_id),
        )
        self._commit()

    def delete(self, template_id: int):
        self._execute("DELETE FROM stat_templates WHERE id = ?", (template_id,))
        self._commit()
