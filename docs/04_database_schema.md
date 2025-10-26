# Migrations

Add tables (suggested)
```sql
CREATE TABLE IF NOT EXISTS turns (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL,
  model_name TEXT,
  started_at TEXT,
  latency_ms INTEGER,
  prompt_tokens INTEGER,
  completion_tokens INTEGER,
  outcome TEXT,
  FOREIGN KEY (session_id) REFERENCES sessions (id)
);

CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  turn_id INTEGER NOT NULL,
  role TEXT NOT NULL,
  content_json TEXT NOT NULL,
  created_at TEXT,
  FOREIGN KEY (turn_id) REFERENCES turns (id)
);

CREATE TABLE IF NOT EXISTS tool_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  turn_id INTEGER NOT NULL,
  tool_name TEXT NOT NULL,
  args_json TEXT,
  result_json TEXT,
  started_at TEXT,
  latency_ms INTEGER,
  success INTEGER,
  FOREIGN KEY (turn_id) REFERENCES turns (id)
);

CREATE TABLE IF NOT EXISTS entities (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL,
  type TEXT NOT NULL,
  key TEXT NOT NULL,
  json TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  updated_at TEXT,
  UNIQUE(session_id, type, key),
  FOREIGN KEY (session_id) REFERENCES sessions (id)
);

CREATE TABLE IF NOT EXISTS memory (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL,
  kind TEXT NOT NULL,
  content_json TEXT NOT NULL,
  embedding BLOB,
  score REAL,
  tags TEXT,
  created_at TEXT,
  updated_at TEXT,
  FOREIGN KEY (session_id) REFERENCES sessions (id)
);