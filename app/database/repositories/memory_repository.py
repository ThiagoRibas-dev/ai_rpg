"""Repository for memory operations."""

import json
from typing import List, Optional, Any, Dict, Union
from app.models.memory import Memory
from .base_repository import BaseRepository


class MemoryRepository(BaseRepository):
    """Handles all memory-related database operations."""

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                kind TEXT NOT NULL,
                content TEXT NOT NULL,
                priority INTEGER DEFAULT 3,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fictional_time TEXT,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
            );
            """
        )
        self.conn.commit()

    def create(
        self,
        session_id: int,
        kind: str,
        content: str,
        priority: int = 3,
        tags: List[str] | None = None,
        fictional_time: str | None = None,
    ) -> Memory:
        tags_json = json.dumps(tags or [])
        cursor = self._execute(
            """INSERT INTO memories 
            (session_id, kind, content, priority, tags, fictional_time) 
            VALUES (?, ?, ?, ?, ?, ?)""",
            (session_id, kind, content, priority, tags_json, fictional_time),
        )
        self._commit()
        return self.get_by_id(cursor.lastrowid)

    def get_by_id(self, memory_id: int) -> Optional[Memory]:
        row = self._fetchone("""SELECT * FROM memories WHERE id = ?""", (memory_id,))
        return Memory(**dict(row)) if row else None

    def get_by_session(self, session_id: int) -> List[Memory]:
        rows = self._fetchall(
            """SELECT * FROM memories WHERE session_id = ? ORDER BY created_at DESC""",
            (session_id,),
        )
        return [Memory(**dict(row)) for row in rows]

    def query(
        self,
        session_id: int,
        kind: Union[str, List[str], None] = None,
        tags: List[str] | None = None,
        query_text: str | None = None,
        limit: int = 10,
    ) -> List[Memory]:
        """Query memories with filters. Kind can be a string or list of strings."""
        query = """SELECT * FROM memories WHERE session_id = ?"""
        params: List[Any] = [session_id]

        if kind:
            if isinstance(kind, list):
                placeholders = ",".join(["?"] * len(kind))
                query += f" AND kind IN ({placeholders})"
                params.extend(kind)
            else:
                query += " AND kind = ?"
                params.append(kind)

        if query_text:
            query += " AND content LIKE ?"
            params.append(f"%{query_text}%")

        if tags:
            tag_conditions = " OR ".join(["tags LIKE ?" for _ in tags])
            query += f" AND ({tag_conditions})"
            for tag in tags:
                params.append(f'%"{tag}"%')

        query += " ORDER BY priority DESC, last_accessed DESC LIMIT ?"
        params.append(limit)

        rows = self._fetchall(query, tuple(params))
        return [Memory(**dict(row)) for row in rows]

    def update_access(self, memory_id: int):
        self._execute(
            """UPDATE memories SET last_accessed = CURRENT_TIMESTAMP, access_count = access_count + 1 WHERE id = ?""",
            (memory_id,),
        )
        self._commit()

    def update(self, memory_id: int, **kwargs) -> Optional[Memory]:
        updates = []
        params = []
        for k, v in kwargs.items():
            if v is not None:
                updates.append(f"{k} = ?")
                params.append(json.dumps(v) if k == "tags" else v)

        if not updates:
            return self.get_by_id(memory_id)

        params.append(memory_id)
        self._execute(
            f"UPDATE memories SET {', '.join(updates)} WHERE id = ?", tuple(params)
        )
        self._commit()
        return self.get_by_id(memory_id)

    def delete(self, memory_id: int):
        self._execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        self._commit()

    def get_statistics(self, session_id: int) -> Dict[str, Any]:
        rows = self._fetchall(
            "SELECT kind, COUNT(*) as count FROM memories WHERE session_id = ? GROUP BY kind",
            (session_id,),
        )
        by_kind = {row["kind"]: row["count"] for row in rows}
        return {"by_kind": by_kind}
