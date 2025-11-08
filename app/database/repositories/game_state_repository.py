"""Repository for game state operations."""

import json
from typing import Any, Dict
from .base_repository import BaseRepository


class GameStateRepository(BaseRepository):
    """Handles all game state related database operations."""

    def get_entity(self, session_id: int, entity_type: str, entity_key: str) -> dict:
        """Retrieve a single entity's state."""
        row = self._fetchone(
            """SELECT state_data FROM game_state 
               WHERE session_id = ? AND entity_type = ? AND entity_key = ?""",
            (session_id, entity_type, entity_key),
        )
        if row and row["state_data"]:
            try:
                return json.loads(row["state_data"])
            except json.JSONDecodeError:
                return {}
        return {}

    def set_entity(
        self, session_id: int, entity_type: str, entity_key: str, state_data: dict
    ) -> int:
        """Create or update an entity's state. Returns version number."""
        state_json = json.dumps(state_data)

        cursor = self._execute(
            """INSERT INTO game_state (session_id, entity_type, entity_key, state_data, version)
               VALUES (?, ?, ?, ?, 1)
               ON CONFLICT(session_id, entity_type, entity_key) 
               DO UPDATE SET 
                   state_data = excluded.state_data,
                   version = version + 1,
                   updated_at = CURRENT_TIMESTAMP
               RETURNING version""",
            (session_id, entity_type, entity_key, state_json),
        )
        row = cursor.fetchone()
        self._commit()
        return row["version"] if row else 1

    def get_all_entities_by_type(self, session_id: int, entity_type: str) -> dict:
        """Get all entities of a specific type for a session. Returns {key: data} dict."""
        rows = self._fetchall(
            """SELECT entity_key, state_data FROM game_state 
               WHERE session_id = ? AND entity_type = ?
               ORDER BY entity_key""",
            (session_id, entity_type),
        )

        results = {}
        for row in rows:
            key = row["entity_key"]
            try:
                data = json.loads(row["state_data"])
                results[key] = data
            except json.JSONDecodeError:
                continue

        return results

    def delete_entity(self, session_id: int, entity_type: str, entity_key: str):
        """Delete a specific entity."""
        self._execute(
            """DELETE FROM game_state 
               WHERE session_id = ? AND entity_type = ? AND entity_key = ?""",
            (session_id, entity_type, entity_key),
        )
        self._commit()

    def get_all(self, session_id: int) -> Dict[str, Dict[str, Any]]:
        """Get all game state for a session, organized by entity type."""
        rows = self._fetchall(
            """SELECT entity_type, entity_key, state_data, version, updated_at
               FROM game_state 
               WHERE session_id = ?
               ORDER BY entity_type, entity_key""",
            (session_id,),
        )

        state: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            entity_type = row["entity_type"]
            entity_key = row["entity_key"]

            if entity_type not in state:
                state[entity_type] = {}

            try:
                data = json.loads(row["state_data"])
                state[entity_type][entity_key] = {
                    "data": data,
                    "version": row["version"],
                    "updated_at": row["updated_at"],
                }
            except json.JSONDecodeError:
                continue

        return state

    def get_statistics(self, session_id: int) -> dict:
        """Get statistics about game state for a session."""
        rows = self._fetchall(
            """SELECT entity_type, COUNT(*) as count 
               FROM game_state 
               WHERE session_id = ? 
               GROUP BY entity_type""",
            (session_id,),
        )

        by_type = {row["entity_type"]: row["count"] for row in rows}

        row = self._fetchone(
            "SELECT COUNT(*) as total FROM game_state WHERE session_id = ?",
            (session_id,),
        )
        total = row["total"]

        return {"total_entities": total, "by_type": by_type}

    def clear(self, session_id: int):
        """Delete all game state for a session (use with caution!)."""
        self._execute("DELETE FROM game_state WHERE session_id = ?", (session_id,))
        self._commit()
