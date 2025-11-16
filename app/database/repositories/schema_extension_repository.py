"""Repository for schema extension operations."""

import json
from typing import Any, Dict
from .base_repository import BaseRepository


class SchemaExtensionRepository(BaseRepository):
    """Handles all schema extension related database operations."""

    def create_table(self):
        """Creates the schema_extensions table."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_extensions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                entity_type TEXT NOT NULL,
                property_name TEXT NOT NULL,
                definition TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (session_id, entity_type, property_name),
                FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
            );
            """
        )
        self.conn.commit()

    def create(
        self,
        session_id: int,
        entity_type: str,
        property_name: str,
        definition_dict: Dict[str, Any],
    ):
        """Create a new schema extension definition."""
        definition_json = json.dumps(definition_dict)
        self._execute(
            """INSERT INTO schema_extensions (session_id, entity_type, property_name, definition)
               VALUES (?, ?, ?, ?)""",
            (session_id, entity_type, property_name, definition_json),
        )
        self._commit()

    def get_by_entity_type(
        self, session_id: int, entity_type: str
    ) -> Dict[str, Dict[str, Any]]:
        """Get all schema extensions for a given session and entity type."""
        rows = self._fetchall(
            """SELECT property_name, definition FROM schema_extensions
               WHERE session_id = ? AND entity_type = ?""",
            (session_id, entity_type),
        )
        return {row["property_name"]: json.loads(row["definition"]) for row in rows}

    def delete(self, session_id: int, entity_type: str, property_name: str):
        """Delete a specific schema extension."""
        self._execute(
            """DELETE FROM schema_extensions
               WHERE session_id = ? AND entity_type = ? AND property_name = ?""",
            (session_id, entity_type, property_name),
        )
        self._commit()

    def get_all(self, session_id: int) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Get all schema extensions for a session, organized by entity type."""
        rows = self._fetchall(
            """SELECT entity_type, property_name, definition FROM schema_extensions
               WHERE session_id = ?
               ORDER BY entity_type, property_name""",
            (session_id,),
        )
        results: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for row in rows:
            entity_type = row["entity_type"]
            if entity_type not in results:
                results[entity_type] = {}
            results[entity_type][row["property_name"]] = json.loads(row["definition"])
        return results
