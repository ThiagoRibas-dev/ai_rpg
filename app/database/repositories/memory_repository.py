"""Repository for memory operations."""

import json
from typing import List, Optional, Any, Dict
from app.models.memory import Memory
from .base_repository import BaseRepository


class MemoryRepository(BaseRepository):
    """Handles all memory-related database operations."""

    def create_table(self):
        """Creates the memories table."""
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
        """Create a new memory entry."""
        tags_json = json.dumps(tags or [])

        cursor = self._execute(
            """INSERT INTO memories 
            (session_id, kind, content, priority, tags, fictional_time) 
            VALUES (?, ?, ?, ?, ?, ?)""",
            (session_id, kind, content, priority, tags_json, fictional_time),
        )
        self._commit()
        memory_id = cursor.lastrowid
        if memory_id is None:
            raise ValueError("Failed to retrieve memory ID after insertion.")
        memory = self.get_by_id(memory_id)
        if memory is None:
            raise ValueError(f"Failed to retrieve created memory with ID {memory_id}.")
        return memory

    def get_by_id(self, memory_id: int) -> Optional[Memory]:
        """Get a single memory by ID."""
        row = self._fetchone(
            """SELECT id, session_id, kind, content, priority, tags, 
                    created_at, fictional_time, last_accessed, access_count 
            FROM memories 
            WHERE id = ?""",
            (memory_id,),
        )
        return Memory(**dict(row)) if row else None

    def get_by_session(self, session_id: int) -> List[Memory]:
        """Get all memories for a session."""
        rows = self._fetchall(
            """SELECT id, session_id, kind, content, priority, tags, 
                    created_at, fictional_time, last_accessed, access_count 
            FROM memories 
            WHERE session_id = ? 
            ORDER BY created_at DESC""",
            (session_id,),
        )
        return [Memory(**dict(row)) for row in rows]

    def query(
        self,
        session_id: int,
        kind: str | None = None,
        tags: List[str] | None = None,
        time_query: str | None = None,
        query_text: str | None = None,
        limit: int = 10,
    ) -> List[Memory]:
        """Query memories with filters."""
        query = """SELECT id, session_id, kind, content, priority, tags, 
                        created_at, fictional_time, last_accessed, access_count 
                FROM memories 
                WHERE session_id = ?"""
        params: List[Any] = [session_id]

        if kind:
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
        
        if time_query:
            query += " AND fictional_time LIKE ?"
            params.append(f"%{time_query}%")

        query += " ORDER BY priority DESC, last_accessed DESC, created_at DESC LIMIT ?"
        params.append(limit)

        rows = self._fetchall(query, tuple(params))
        return [Memory(**dict(row)) for row in rows]

    def update_access(self, memory_id: int):
        """Update access timestamp and increment access count."""
        self._execute(
            """UPDATE memories 
            SET last_accessed = CURRENT_TIMESTAMP, 
                access_count = access_count + 1 
            WHERE id = ?""",
            (memory_id,),
        )
        self._commit()

    def update(
        self,
        memory_id: int,
        kind: str | None = None,
        content: str | None = None,
        priority: int | None = None,
        tags: List[str] | None = None,
    ) -> Optional[Memory]:
        """Update a memory's kind, content, priority, or tags."""
        updates = []
        params: List[Any] = []

        if kind is not None:
            updates.append("kind = ?")
            params.append(kind)

        if content is not None:
            updates.append("content = ?")
            params.append(content)

        if priority is not None:
            updates.append("priority = ?")
            params.append(priority)

        if tags is not None:
            updates.append("tags = ?")
            params.append(json.dumps(tags))

        if not updates:
            return self.get_by_id(memory_id)

        params.append(memory_id)
        query = f"UPDATE memories SET {', '.join(updates)} WHERE id = ?"

        self._execute(query, tuple(params))
        self._commit()

        return self.get_by_id(memory_id)

    def delete(self, memory_id: int):
        """Delete a memory."""
        self._execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        self._commit()

    def get_statistics(self, session_id: int) -> Dict[str, Any]:
        """Get statistics about memories for a session."""
        # Total by kind
        rows = self._fetchall(
            """SELECT kind, COUNT(*) as count 
            FROM memories 
            WHERE session_id = ? 
            GROUP BY kind""",
            (session_id,),
        )
        by_kind = {row["kind"]: row["count"] for row in rows}

        # Most accessed
        rows = self._fetchall(
            """SELECT id, content, access_count 
            FROM memories 
            WHERE session_id = ? 
            ORDER BY access_count DESC 
            LIMIT 5""",
            (session_id,),
        )
        most_accessed = [dict(row) for row in rows]

        # Total count
        row = self._fetchone(
            "SELECT COUNT(*) as total FROM memories WHERE session_id = ?", (session_id,)
        )
        total = row["total"] if row else 0

        return {"total": total, "by_kind": by_kind, "most_accessed": most_accessed}
