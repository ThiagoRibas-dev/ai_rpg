"""Repository for SystemManifest operations."""

from typing import List, Optional, Dict, Any
from .base_repository import BaseRepository
from app.prefabs.manifest import SystemManifest


class ManifestRepository(BaseRepository):
    """
    Handles database operations for SystemManifests.
    Stores the configuration for game systems (D&D, CoC, etc).
    """

    def create_table(self):
        """Creates the manifests table."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS manifests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                system_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                data_json TEXT NOT NULL,
                is_builtin BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        self.conn.commit()

    def create(self, manifest: SystemManifest, is_builtin: bool = False) -> int:
        """
        Save a new Manifest to the database. Returns the new ID.
        """
        data_str = manifest.to_json()
        
        cursor = self._execute(
            """INSERT INTO manifests (system_id, name, data_json, is_builtin) 
               VALUES (?, ?, ?, ?)""",
            (manifest.id, manifest.name, data_str, 1 if is_builtin else 0),
        )
        self._commit()
        
        if cursor.lastrowid:
            return cursor.lastrowid
        raise ValueError("Failed to create manifest")

    def update(self, manifest_id: int, manifest: SystemManifest):
        """Update an existing manifest."""
        data_str = manifest.to_json()
        self._execute(
            "UPDATE manifests SET system_id = ?, name = ?, data_json = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (manifest.id, manifest.name, data_str, manifest_id),
        )
        self._commit()

    def upsert_builtin(self, manifest: SystemManifest) -> int:
        """
        Update a built-in manifest if it exists, or create it if not.
        Uses system_id as the key.
        """
        existing = self.get_by_system_id(manifest.id)
        if existing:
            # We need the numeric ID to update
            row = self._fetchone("SELECT id FROM manifests WHERE system_id = ?", (manifest.id,))
            if row:
                self.update(row["id"], manifest)
                return row["id"]
        
        return self.create(manifest, is_builtin=True)

    def get_by_id(self, manifest_id: int) -> Optional[SystemManifest]:
        """Retrieve a Manifest by numeric ID."""
        row = self._fetchone(
            "SELECT data_json FROM manifests WHERE id = ?", (manifest_id,)
        )
        if row:
            try:
                return SystemManifest.from_json(row["data_json"])
            except Exception:
                return None
        return None

    def get_by_system_id(self, system_id: str) -> Optional[SystemManifest]:
        """Retrieve a Manifest by string ID (e.g. 'dnd_5e')."""
        row = self._fetchone(
            "SELECT data_json FROM manifests WHERE system_id = ?", (system_id,)
        )
        if row:
            try:
                return SystemManifest.from_json(row["data_json"])
            except Exception:
                return None
        return None

    def get_all(self) -> List[Dict[str, Any]]:
        """
        Get all manifests (metadata only).
        Returns list of dicts: {'id', 'system_id', 'name', 'is_builtin'}
        """
        rows = self._fetchall("SELECT id, system_id, name, is_builtin FROM manifests ORDER BY name")
        return [dict(row) for row in rows]

    def delete(self, manifest_id: int):
        """Delete a manifest."""
        self._execute("DELETE FROM manifests WHERE id = ?", (manifest_id,))
        self._commit()
