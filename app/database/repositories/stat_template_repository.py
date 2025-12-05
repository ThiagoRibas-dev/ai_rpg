from typing import List, Optional, Any
from .base_repository import BaseRepository
from app.models.sheet_schema import CharacterSheetSpec


class StatTemplateRepository(BaseRepository):
    """
    Handles database operations for CharacterSheetSpec.
    """

    def create_table(self):
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

    def create(self, ruleset_id: int, template: Any) -> int:
        data_str = template.model_dump_json()

        # Determine name
        name = "Character Sheet Template"

        cursor = self._execute(
            """INSERT INTO stat_templates (ruleset_id, name, data_json) 
               VALUES (?, ?, ?)""",
            (ruleset_id, name, data_str),
        )
        self._commit()
        if cursor.lastrowid:
            return cursor.lastrowid
        raise ValueError("Failed to create stat template")

    def get_by_id(self, template_id: int) -> Optional[CharacterSheetSpec]:
        row = self._fetchone(
            "SELECT data_json FROM stat_templates WHERE id = ?", (template_id,)
        )
        if row:
            try:
                return CharacterSheetSpec.model_validate_json(row["data_json"])
            except Exception:
                # If migration failed or old data exists, return None or handle gracefully
                return None
        return None

    def get_by_ruleset(self, ruleset_id: int) -> List[dict]:
        rows = self._fetchall(
            "SELECT id, name FROM stat_templates WHERE ruleset_id = ? ORDER BY name",
            (ruleset_id,),
        )
        return [{"id": row["id"], "name": row["name"]} for row in rows]

    def update(self, template_id: int, template: Any):
        data_str = template.model_dump_json()
        name = "Updated Template"
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
