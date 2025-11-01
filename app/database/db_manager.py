import sqlite3
from typing import List, Dict, Optional, Any
from datetime import datetime
from app.models.prompt import Prompt
from app.models.game_session import GameSession
from app.models.world_info import WorldInfo
from app.models.memory import Memory

class DBManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

    def create_tables(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS prompts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    content TEXT NOT NULL
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    session_data TEXT NOT NULL,
                    prompt_id INTEGER NOT NULL,
                    memory TEXT DEFAULT '',
                    authors_note TEXT DEFAULT '',
                    FOREIGN KEY (prompt_id) REFERENCES prompts (id)
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS world_info (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prompt_id INTEGER NOT NULL,
                    keywords TEXT NOT NULL,
                    content TEXT NOT NULL,
                    FOREIGN KEY (prompt_id) REFERENCES prompts (id)
                )
            """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                kind TEXT NOT NULL,
                content TEXT NOT NULL,
                priority INTEGER NOT NULL DEFAULT 3,
                tags TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
            )
        """)
        
        # Create indexes for performance
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_session 
            ON memories(session_id)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_kind 
            ON memories(kind)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_priority 
            ON memories(priority)
        """)

    # ==================== Prompts ====================
    def create_prompt(self, name: str, content: str) -> Prompt:
        with self.conn:
            cursor = self.conn.execute("INSERT INTO prompts (name, content) VALUES (?, ?)", (name, content))
            return Prompt(id=cursor.lastrowid, name=name, content=content)

    def get_all_prompts(self) -> List[Prompt]:
        with self.conn:
            cursor = self.conn.execute("SELECT id, name, content FROM prompts")
            return [Prompt(**row) for row in cursor.fetchall()]

    def update_prompt(self, prompt: Prompt):
        with self.conn:
            self.conn.execute("UPDATE prompts SET name = ?, content = ? WHERE id = ?", 
                            (prompt.name, prompt.content, prompt.id))

    def delete_prompt(self, prompt_id: int):
        with self.conn:
            self.conn.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))

    # ==================== Sessions ====================
    def save_session(self, name: str, session_data: str, prompt_id: int) -> GameSession:
        with self.conn:
            cursor = self.conn.execute(
                "INSERT INTO sessions (name, session_data, prompt_id, memory, authors_note) VALUES (?, ?, ?, '', '')", 
                (name, session_data, prompt_id)
            )
            return GameSession(
                id=cursor.lastrowid, 
                name=name, 
                session_data=session_data, 
                prompt_id=prompt_id,
                memory="",
                authors_note=""
            )

    def load_session(self, session_id: int) -> GameSession | None:
        with self.conn:
            cursor = self.conn.execute(
                "SELECT id, name, session_data, prompt_id, memory, authors_note FROM sessions WHERE id = ?", 
                (session_id,)
            )
            row = cursor.fetchone()
            if row:
                return GameSession(
                    id=row["id"],
                    name=row["name"],
                    session_data=row["session_data"],
                    prompt_id=row["prompt_id"],
                    memory=row["memory"] or "",
                    authors_note=row["authors_note"] or ""
                )
            return None

    def get_all_sessions(self) -> List[GameSession]:
        with self.conn:
            cursor = self.conn.execute("SELECT id, name, session_data, prompt_id, memory, authors_note FROM sessions")
            return [GameSession(**row) for row in cursor.fetchall()]

    def get_sessions_by_prompt(self, prompt_id: int) -> List[GameSession]:
        with self.conn:
            cursor = self.conn.execute(
                "SELECT id, name, session_data, prompt_id, memory, authors_note FROM sessions WHERE prompt_id = ?", 
                (prompt_id,)
            )
            return [GameSession(**row) for row in cursor.fetchall()]

    def update_session(self, session: GameSession):
        with self.conn:
            self.conn.execute(
                "UPDATE sessions SET name = ?, session_data = ?, prompt_id = ?, memory = ?, authors_note = ? WHERE id = ?",
                (session.name, session.session_data, session.prompt_id, session.memory, session.authors_note, session.id)
            )

    def update_session_context(self, session_id: int, memory: str, authors_note: str):
        """Update only the context fields of a session."""
        with self.conn:
            self.conn.execute(
                "UPDATE sessions SET memory = ?, authors_note = ? WHERE id = ?",
                (memory, authors_note, session_id)
            )

    def get_session_context(self, session_id: int) -> Optional[Dict[str, str]]:
        """Retrieve the context fields for a session."""
        with self.conn:
            cursor = self.conn.execute(
                "SELECT memory, authors_note FROM sessions WHERE id = ?",
                (session_id,)
            )
            row = cursor.fetchone()
            if row:
                return {"memory": row["memory"] or "", "authors_note": row["authors_note"] or ""}
            return None

    # ==================== World Info ====================
    def create_world_info(self, prompt_id: int, keywords: str, content: str) -> WorldInfo:
        with self.conn:
            cursor = self.conn.execute(
                "INSERT INTO world_info (prompt_id, keywords, content) VALUES (?, ?, ?)",
                (prompt_id, keywords, content)
            )
            return WorldInfo(id=cursor.lastrowid, prompt_id=prompt_id, keywords=keywords, content=content)

    def get_world_info_by_prompt(self, prompt_id: int) -> List[WorldInfo]:
        with self.conn:
            cursor = self.conn.execute(
                "SELECT id, prompt_id, keywords, content FROM world_info WHERE prompt_id = ?",
                (prompt_id,)
            )
            return [WorldInfo(**row) for row in cursor.fetchall()]

    def update_world_info(self, world_info: WorldInfo):
        with self.conn:
            self.conn.execute(
                "UPDATE world_info SET keywords = ?, content = ? WHERE id = ?",
                (world_info.keywords, world_info.content, world_info.id)
            )

    def delete_world_info(self, world_info_id: int):
        with self.conn:
            self.conn.execute("DELETE FROM world_info WHERE id = ?", (world_info_id,))

    # ==================== Memories ====================
    def create_memory(self, session_id: int, kind: str, content: str, 
                    priority: int = 3, tags: List[str] | None = None) -> Memory:
        """Create a new memory entry."""
        import json
        tags_json = json.dumps(tags or [])
        
        with self.conn:
            cursor = self.conn.execute(
                """INSERT INTO memories 
                (session_id, kind, content, priority, tags) 
                VALUES (?, ?, ?, ?, ?)""",
                (session_id, kind, content, priority, tags_json)
            )
            
            return Memory(
                id=cursor.lastrowid,
                session_id=session_id,
                kind=kind,
                content=content,
                priority=priority,
                tags=tags_json,
                created_at=datetime.now().isoformat(),
                last_accessed=None,
                access_count=0
            )

    def get_memories_by_session(self, session_id: int) -> List[Memory]:
        """Get all memories for a session."""
        from app.models.memory import Memory
        
        with self.conn:
            cursor = self.conn.execute(
                """SELECT id, session_id, kind, content, priority, tags, 
                        created_at, last_accessed, access_count 
                FROM memories 
                WHERE session_id = ? 
                ORDER BY created_at DESC""",
                (session_id,)
            )
            return [Memory(**row) for row in cursor.fetchall()]

    def query_memories(self, session_id: int, kind: str | None = None, 
                    tags: List[str] | None = None, query_text: str | None = None,
                    limit: int = 10) -> List[Memory]:
        """Query memories with filters."""
        from app.models.memory import Memory
        
        query = """SELECT id, session_id, kind, content, priority, tags, 
                        created_at, last_accessed, access_count 
                FROM memories 
                WHERE session_id = ?"""
        params = [session_id]
        
        if kind:
            query += " AND kind = ?"
            params.append(kind)
        
        if query_text:
            query += " AND content LIKE ?"
            params.append(f"%{query_text}%")
        
        # Tag filtering - check if any of the provided tags match
        if tags:
            tag_conditions = " OR ".join(["tags LIKE ?" for _ in tags])
            query += f" AND ({tag_conditions})"
            for tag in tags:
                params.append(f'%"{tag}"%')
        
        query += " ORDER BY priority DESC, last_accessed DESC, created_at DESC LIMIT ?"
        params.append(limit)
        
        with self.conn:
            cursor = self.conn.execute(query, params)
            return [Memory(**row) for row in cursor.fetchall()]

    def update_memory_access(self, memory_id: int):
        """Update access timestamp and increment access count."""
        with self.conn:
            self.conn.execute(
                """UPDATE memories 
                SET last_accessed = CURRENT_TIMESTAMP, 
                    access_count = access_count + 1 
                WHERE id = ?""",
                (memory_id,)
            )

    def update_memory(self, memory_id: int, kind: str | None = None, content: str | None = None, 
                  priority: int | None = None, tags: List[str] | None = None) -> Memory:
        """Update a memory's kind, content, priority, or tags."""
        import json
        
        updates = []
        params = []
        
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
            return self.get_memory_by_id(memory_id)
        
        params.append(memory_id)
        query = f"UPDATE memories SET {', '.join(updates)} WHERE id = ?"
        
        with self.conn:
            self.conn.execute(query, params)
        
        return self.get_memory_by_id(memory_id)

    def get_memory_by_id(self, memory_id: int) -> Memory | None:
        """Get a single memory by ID."""
        from app.models.memory import Memory
        
        with self.conn:
            cursor = self.conn.execute(
                """SELECT id, session_id, kind, content, priority, tags, 
                        created_at, last_accessed, access_count 
                FROM memories 
                WHERE id = ?""",
                (memory_id,)
            )
            row = cursor.fetchone()
            if row:
                return Memory(**row)
            return None

    def delete_memory(self, memory_id: int):
        """Delete a memory."""
        with self.conn:
            self.conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))

    def get_memory_statistics(self, session_id: int) -> Dict[str, Any]:
        """Get statistics about memories for a session."""
        with self.conn:
            # Total by kind
            cursor = self.conn.execute(
                """SELECT kind, COUNT(*) as count 
                FROM memories 
                WHERE session_id = ? 
                GROUP BY kind""",
                (session_id,)
            )
            by_kind = {row["kind"]: row["count"] for row in cursor.fetchall()}
            
            # Most accessed
            cursor = self.conn.execute(
                """SELECT id, content, access_count 
                FROM memories 
                WHERE session_id = ? 
                ORDER BY access_count DESC 
                LIMIT 5""",
                (session_id,)
            )
            most_accessed = [dict(row) for row in cursor.fetchall()]
            
            # Total count
            cursor = self.conn.execute(
                "SELECT COUNT(*) as total FROM memories WHERE session_id = ?",
                (session_id,)
            )
            total = cursor.fetchone()["total"]
            
            return {
                "total": total,
                "by_kind": by_kind,
                "most_accessed": most_accessed
            }