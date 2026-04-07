"""Repository for memory operations."""

import json
from typing import Any

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

        # 1. Create FTS Virtual Table
        cursor.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
            USING fts5(content, tags, content=memories, content_rowid=id, tokenize='porter');
            """
        )

        # 2. Add Triggers to keep FTS strictly synced with main table (External Content Pattern)
        cursor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
              INSERT INTO memories_fts(rowid, content, tags) VALUES (new.id, new.content, new.tags);
            END;
            """
        )
        cursor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
              INSERT INTO memories_fts(memories_fts, rowid, content, tags) VALUES('delete', old.id, old.content, old.tags);
            END;
            """
        )
        cursor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
              INSERT INTO memories_fts(memories_fts, rowid, content, tags) VALUES('delete', old.id, old.content, old.tags);
              INSERT INTO memories_fts(rowid, content, tags) VALUES (new.id, new.content, new.tags);
            END;
            """
        )

        # 3. Handle backwards compatibility (one-time sync for existing rows missing from FTS)
        cursor.execute(
            """
            INSERT INTO memories_fts(rowid, content, tags)
            SELECT id, content, tags FROM memories
            WHERE id NOT IN (SELECT rowid FROM memories_fts);
            """
        )
        self.conn.commit()

    def create(
        self,
        session_id: int,
        kind: str,
        content: str,
        priority: int = 3,
        tags: list[str] | None = None,
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
        if cursor.lastrowid is None:
            raise RuntimeError("Failed to retrieve lastrowid after memory creation.")
        memory = self.get_by_id(int(cursor.lastrowid))
        if memory is None:
            raise RuntimeError(f"Failed to retrieve memory after creation with ID {cursor.lastrowid}")
        return memory

    def get_by_id(self, memory_id: int) -> Memory | None:
        row = self._fetchone("""SELECT * FROM memories WHERE id = ?""", (memory_id,))
        return Memory(**dict(row)) if row else None

    def get_by_session(self, session_id: int) -> list[Memory]:
        rows = self._fetchall(
            """SELECT * FROM memories WHERE session_id = ? ORDER BY created_at DESC""",
            (session_id,),
        )
        return [Memory(**dict(row)) for row in rows]

    def query(
        self,
        session_id: int,
        kind: str | list[str] | None = None,
        tags: list[str] | None = None,
        query_text: str | None = None,
        limit: int = 10,
    ) -> list[Memory]:
        """Query memories with filters. Kind can be a string or list of strings."""
        query = """SELECT * FROM memories WHERE session_id = ?"""
        params: list[Any] = [session_id]

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

    def update(self, memory_id: int, **kwargs) -> Memory | None:
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
        memory = self.get_by_id(memory_id)
        if memory is None:
            raise RuntimeError(f"Failed to retrieve memory after update with ID {memory_id}")
        return memory

    def delete(self, memory_id: int):
        self._execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        self._commit()

    def get_statistics(self, session_id: int) -> dict[str, Any]:
        rows = self._fetchall(
            "SELECT kind, COUNT(*) as count FROM memories WHERE session_id = ? GROUP BY kind",
            (session_id,),
        )
        by_kind = {row["kind"]: row["count"] for row in rows}
        return {"by_kind": by_kind}

    def search_bm25(
        self, session_id: int, query_text: str, limit: int = 15
    ) -> list[tuple[Memory, float]]:
        """Search memories using BM25 ranking via FTS5."""
        # Format for FTS5 (escape quotes, simple OR query for robustness)
        words = [w for w in query_text.replace('"', "").split() if w.isalnum()]
        if not words:
            return []

        fts_query = " OR ".join(words)

        # We invert the bm25 score so that higher = better for downstream logic
        query = """
            SELECT m.*, -bm25(memories_fts) as score
            FROM memories_fts fts
            JOIN memories m ON fts.rowid = m.id
            WHERE memories_fts MATCH ? AND m.session_id = ?
            ORDER BY bm25(memories_fts)
            LIMIT ?
        """
        rows = self._fetchall(query, (fts_query, session_id, limit))
        return [(Memory(**dict(r)), float(r["score"])) for r in rows]
