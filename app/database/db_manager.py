import sqlite3
from typing import List, Dict, Optional, Any
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
                    game_time TEXT DEFAULT 'Day 1, Dawn',  -- NEW
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
                    fictional_time TEXT DEFAULT NULL,  -- NEW: "Day 3, 14:30" or "3 hours into dungeon"
                    last_accessed TIMESTAMP,
                    access_count INTEGER DEFAULT 0,
                    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS turn_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    prompt_id INTEGER NOT NULL,  -- 🆕 Add this
                    round_number INTEGER NOT NULL,
                    summary TEXT NOT NULL,
                    tags TEXT DEFAULT '[]',
                    importance INTEGER DEFAULT 3,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE,
                    FOREIGN KEY (prompt_id) REFERENCES prompts (id)  -- 🆕 Add this
                )
            """)

            # ==================== Schema Extensions ====================
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_extensions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    entity_type TEXT NOT NULL,
                    property_name TEXT NOT NULL,
                    definition TEXT NOT NULL,  -- JSON of PropertyDefinition
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE,
                    UNIQUE(session_id, entity_type, property_name)
                )
            """)
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_schema_extensions ON schema_extensions(session_id, entity_type)
            """)
            
            # Migration for game_mode column
            try:
                self.conn.execute("SELECT game_mode FROM sessions LIMIT 1")
            except sqlite3.OperationalError:
                self.conn.execute("ALTER TABLE sessions ADD COLUMN game_mode TEXT DEFAULT 'SETUP'")

            # Create indexes for performance
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_turn_metadata_session 
                ON turn_metadata(session_id)
            """)
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_turn_metadata_importance 
                ON turn_metadata(importance)
            """)
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
            
            # ==================== Game State ====================
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS game_state (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_key TEXT NOT NULL,
                    state_data TEXT NOT NULL,
                    version INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE,
                    UNIQUE(session_id, entity_type, entity_key)
                )
            """)
            
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_game_state_session 
                ON game_state(session_id)
            """)
            
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_game_state_entity_type 
                ON game_state(entity_type)
            """)
            
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_game_state_lookup 
                ON game_state(session_id, entity_type, entity_key)
            """)

    # ==================== Prompts ====================
    def create_prompt(self, name: str, content: str) -> Prompt:
        with self.conn:
            cursor = self.conn.execute("INSERT INTO prompts (name, content) VALUES (?, ?)", (name, content))
            return Prompt(id=cursor.lastrowid, name=name, content=content)

    def get_all_prompts(self) -> List[Prompt]:
        with self.conn:
            cursor = self.conn.execute("SELECT id, name, content FROM prompts")
            return [Prompt(**dict(row)) for row in cursor.fetchall()]

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
                authors_note="",
                game_mode="SETUP" # Default for new sessions
            )

    def load_session(self, session_id: int) -> GameSession | None:
        with self.conn:
            cursor = self.conn.execute(
                "SELECT id, name, session_data, prompt_id, memory, authors_note, game_time, game_mode FROM sessions WHERE id = ?",
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
                    authors_note=row["authors_note"] or "",
                    game_time=row["game_time"] or "Day 1, Dawn",
                    game_mode=row["game_mode"] or "SETUP" # Added with fallback
                )
            return None

    def get_all_sessions(self) -> List[GameSession]:
        with self.conn:
            cursor = self.conn.execute("SELECT id, name, session_data, prompt_id, memory, authors_note, game_time, game_mode FROM sessions")
            return [GameSession(**dict(row)) for row in cursor.fetchall()]

    def get_sessions_by_prompt(self, prompt_id: int) -> List[GameSession]:
        with self.conn:
            cursor = self.conn.execute(
                "SELECT id, name, session_data, prompt_id, memory, authors_note, game_time, game_mode FROM sessions WHERE prompt_id = ?", 
                (prompt_id,)
            )
            return [GameSession(**dict(row)) for row in cursor.fetchall()]

    def update_session(self, session: GameSession):
        with self.conn:
            self.conn.execute(
                "UPDATE sessions SET name = ?, session_data = ?, prompt_id = ?, memory = ?, authors_note = ?, game_time = ?, game_mode = ? WHERE id = ?",
                (session.name, session.session_data, session.prompt_id, session.memory, session.authors_note, session.game_time, session.game_mode, session.id)
            )

    def update_session_context(self, session_id: int, memory: str, authors_note: str):
        """Update only the context fields of a session."""
        with self.conn:
            self.conn.execute(
                "UPDATE sessions SET memory = ?, authors_note = ? WHERE id = ?",
                (memory, authors_note, session_id)
            )

    def update_session_game_time(self, session_id: int, game_time: str):
        """Update only the fictional game_time field of a session."""
        with self.conn:
            self.conn.execute(
                "UPDATE sessions SET game_time = ? WHERE id = ?",
                (game_time, session_id)
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
            return [WorldInfo(**dict(row)) for row in cursor.fetchall()]

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
                    priority: int = 3, tags: List[str] | None = None,
                    fictional_time: str | None = None) -> Memory:
        """Create a new memory entry."""
        import json
        tags_json = json.dumps(tags or [])
        
        with self.conn:
            cursor = self.conn.execute(
                """INSERT INTO memories 
                (session_id, kind, content, priority, tags, fictional_time) 
                VALUES (?, ?, ?, ?, ?, ?)""",
                (session_id, kind, content, priority, tags_json, fictional_time)
            )
            
            # Get the created memory to return it with actual DB timestamp
            memory_id = cursor.lastrowid
            cursor = self.conn.execute(
                """SELECT id, session_id, kind, content, priority, tags, 
                        created_at, fictional_time, last_accessed, access_count 
                FROM memories 
                WHERE id = ?""",
                (memory_id,)
            )
            row = cursor.fetchone()
            return Memory(**row)

    def get_memories_by_session(self, session_id: int) -> List[Memory]:
        """Get all memories for a session."""
        from app.models.memory import Memory
        
        with self.conn:
            cursor = self.conn.execute(
                """SELECT id, session_id, kind, content, priority, tags, 
                        created_at, fictional_time, last_accessed, access_count 
                FROM memories 
                WHERE session_id = ? 
                ORDER BY created_at DESC""",
                (session_id,)
            )
            return [Memory(**dict(row)) for row in cursor.fetchall()]

    def query_memories(self, session_id: int, kind: str | None = None, 
                    tags: List[str] | None = None, query_text: str | None = None,
                    limit: int = 10) -> List[Memory]:
        """Query memories with filters."""
        from app.models.memory import Memory
        
        query = """SELECT id, session_id, kind, content, priority, tags, 
                        created_at, fictional_time, last_accessed, access_count 
                FROM memories 
                WHERE session_id = ?"""
        params: List[Any] = [session_id] # Changed to List[Any]
        
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
            return [Memory(**dict(row)) for row in cursor.fetchall()]

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
                  priority: int | None = None, tags: List[str] | None = None) -> Optional[Memory]: # Changed return type
        """Update a memory's kind, content, priority, or tags."""
        import json
        
        updates = []
        params: List[Any] = [] # Changed to List[Any]
        
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

    def get_memory_by_id(self, memory_id: int) -> Optional[Memory]: # Changed return type
        """Get a single memory by ID."""
        from app.models.memory import Memory
        
        with self.conn:
            cursor = self.conn.execute(
                """SELECT id, session_id, kind, content, priority, tags, 
                        created_at, fictional_time, last_accessed, access_count 
                FROM memories 
                WHERE id = ?""",
                (memory_id,)
            )
            row = cursor.fetchone()
            if row:
                return Memory(**dict(row))
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

    # ==================== Game State ====================
    def get_game_state_entity(self, session_id: int, entity_type: str, entity_key: str) -> dict:
        """Retrieve a single entity's state."""
        import json
        
        with self.conn:
            cursor = self.conn.execute(
                """SELECT state_data FROM game_state 
                   WHERE session_id = ? AND entity_type = ? AND entity_key = ?""",
                (session_id, entity_type, entity_key)
            )
            row = cursor.fetchone()
            
            if row and row["state_data"]:
                try:
                    return json.loads(row["state_data"])
                except json.JSONDecodeError:
                    return {}
            return {}
    
    def set_game_state_entity(self, session_id: int, entity_type: str, entity_key: str, 
                             state_data: dict) -> int:
        """Create or update an entity's state. Returns version number."""
        import json
        
        state_json = json.dumps(state_data)
        
        with self.conn:
            cursor = self.conn.execute(
                """INSERT INTO game_state (session_id, entity_type, entity_key, state_data, version)
                   VALUES (?, ?, ?, ?, 1)
                   ON CONFLICT(session_id, entity_type, entity_key) 
                   DO UPDATE SET 
                       state_data = excluded.state_data,
                       version = version + 1,
                       updated_at = CURRENT_TIMESTAMP
                   RETURNING version""",
                (session_id, entity_type, entity_key, state_json)
            )
            row = cursor.fetchone()
            return row["version"] if row else 1
    
    def get_all_entities_by_type(self, session_id: int, entity_type: str) -> dict:
        """Get all entities of a specific type for a session. Returns {key: data} dict."""
        import json
        
        with self.conn:
            cursor = self.conn.execute(
                """SELECT entity_key, state_data FROM game_state 
                   WHERE session_id = ? AND entity_type = ?
                   ORDER BY entity_key""",
                (session_id, entity_type)
            )
            
            results = {}
            for row in cursor.fetchall():
                key = row["entity_key"]
                try:
                    data = json.loads(row["state_data"])
                    results[key] = data
                except json.JSONDecodeError:
                    continue
            
            return results
    
    def delete_game_state_entity(self, session_id: int, entity_type: str, entity_key: str):
        """Delete a specific entity."""
        with self.conn:
            self.conn.execute(
                """DELETE FROM game_state 
                   WHERE session_id = ? AND entity_type = ? AND entity_key = ?""",
                (session_id, entity_type, entity_key)
            )
    
    def get_all_game_state(self, session_id: int) -> dict:
        """Get all game state for a session, organized by entity type."""
        import json
        
        with self.conn:
            cursor = self.conn.execute(
                """SELECT entity_type, entity_key, state_data, version, updated_at
                   FROM game_state 
                   WHERE session_id = ?
                   ORDER BY entity_type, entity_key""",
                (session_id,)
            )
            
            state: Dict[str, Dict[str, Any]] = {} # Added type annotation
            for row in cursor.fetchall():
                entity_type = row["entity_type"]
                entity_key = row["entity_key"]
                
                if entity_type not in state:
                    state[entity_type] = {}
                
                try:
                    data = json.loads(row["state_data"])
                    state[entity_type][entity_key] = {
                        "data": data,
                        "version": row["version"],
                        "updated_at": row["updated_at"]
                    }
                except json.JSONDecodeError:
                    continue
            
            return state
    
    def get_game_state_statistics(self, session_id: int) -> dict:
        """Get statistics about game state for a session."""
        with self.conn:
            cursor = self.conn.execute(
                """SELECT entity_type, COUNT(*) as count 
                   FROM game_state 
                   WHERE session_id = ? 
                   GROUP BY entity_type""",
                (session_id,)
            )
            
            by_type = {row["entity_type"]: row["count"] for row in cursor.fetchall()}
            
            cursor = self.conn.execute(
                "SELECT COUNT(*) as total FROM game_state WHERE session_id = ?",
                (session_id,)
            )
            total = cursor.fetchone()["total"]
            
            return {
                "total_entities": total,
                "by_type": by_type
            }
    
    def clear_game_state(self, session_id: int):
        """Delete all game state for a session (use with caution!)."""
        with self.conn:
            self.conn.execute(
                "DELETE FROM game_state WHERE session_id = ?",
                (session_id,)
            )

    # ==================== Schema Extensions ====================
    def create_schema_extension(self, session_id: int, entity_type: str, property_name: str, definition_dict: Dict[str, Any]):
        """Create a new schema extension definition."""
        import json
        definition_json = json.dumps(definition_dict)
        with self.conn:
            self.conn.execute(
                """INSERT INTO schema_extensions (session_id, entity_type, property_name, definition)
                   VALUES (?, ?, ?, ?)""",
                (session_id, entity_type, property_name, definition_json)
            )

    def get_schema_extensions(self, session_id: int, entity_type: str) -> Dict[str, Dict[str, Any]]:
        """Get all schema extensions for a given session and entity type."""
        import json
        with self.conn:
            cursor = self.conn.execute(
                """SELECT property_name, definition FROM schema_extensions
                   WHERE session_id = ? AND entity_type = ?""",
                (session_id, entity_type)
            )
            return {row["property_name"]: json.loads(row["definition"]) for row in cursor.fetchall()}

    def delete_schema_extension(self, session_id: int, entity_type: str, property_name: str):
        """Delete a specific schema extension."""
        with self.conn:
            self.conn.execute(
                """DELETE FROM schema_extensions
                   WHERE session_id = ? AND entity_type = ? AND property_name = ?""",
                (session_id, entity_type, property_name)
            )

    def get_all_schema_extensions(self, session_id: int) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Get all schema extensions for a session, organized by entity type."""
        import json
        with self.conn:
            cursor = self.conn.execute(
                """SELECT entity_type, property_name, definition FROM schema_extensions
                   WHERE session_id = ?
                   ORDER BY entity_type, property_name""",
                (session_id,)
            )
            results = {}
            for row in cursor.fetchall():
                entity_type = row["entity_type"]
                if entity_type not in results:
                    results[entity_type] = {}
                results[entity_type][row["property_name"]] = json.loads(row["definition"])
            return results

    # ==================== Turn Metadata ====================
    # In db_manager.py, create_turn_metadata
    def create_turn_metadata(self, session_id: int, prompt_id: int, round_number: int, 
                            summary: str, tags: List[str], importance: int) -> int:
        """Create a turn metadata entry and return its ID."""
        import json
        tags_json = json.dumps(tags)
        
        with self.conn:
            cursor = self.conn.execute(
                """INSERT INTO turn_metadata 
                (session_id, prompt_id, round_number, summary, tags, importance) 
                VALUES (?, ?, ?, ?, ?, ?)""",
                (session_id, prompt_id, round_number, summary, tags_json, importance)
            )
            return cursor.lastrowid

    def get_turn_metadata_range(self, session_id: int, start_round: int, end_round: int) -> List[Dict[str, Any]]:
        """Get metadata for a range of rounds."""
        import json
        
        with self.conn:
            cursor = self.conn.execute(
                """SELECT round_number, summary, tags, importance 
                FROM turn_metadata 
                WHERE session_id = ? AND round_number BETWEEN ? AND ?
                ORDER BY round_number ASC""",
                (session_id, start_round, end_round)
            )
            results = []
            for row in cursor.fetchall():
                results.append({
                    "round_number": row["round_number"],
                    "summary": row["summary"],
                    "tags": json.loads(row["tags"]),
                    "importance": row["importance"]
                })
            return results

    def get_all_turn_metadata(self, session_id: int) -> List[Dict[str, Any]]:
        """Get all metadata for a session."""
        import json
        
        with self.conn:
            cursor = self.conn.execute(
                """SELECT round_number, summary, tags, importance 
                FROM turn_metadata 
                WHERE session_id = ?
                ORDER BY round_number ASC""",
                (session_id,)
            )
            results = []
            for row in cursor.fetchall():
                results.append({
                    "round_number": row["round_number"],
                    "summary": row["summary"],
                    "tags": json.loads(row["tags"]),
                    "importance": row["importance"]
                })
            return results
