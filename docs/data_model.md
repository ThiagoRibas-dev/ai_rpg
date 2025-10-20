# Data Model (SQLite with JSON and FKs)

- **sessions**(id, created_at, title, provider, system_preset)
- **turns**(id, session_id, user_text, model_name, prompt_tokens, completion_tokens, started_at, latency_ms, outcome)
- **messages**(id, turn_id, role, content_json, created_at)
- **tool_events**(id, turn_id, tool_name, args_json, result_json, started_at, latency_ms, success)
- **memory**(id, session_id, kind, content_json, embedding, score, tags, created_at, updated_at)
  - `kind` ∈ {episodic, semantic, lore, user_pref}
- **world_entities**(id, session_id, type, key, json, version, updated_at)
  - `type` ∈ {character, location, item, quest, rule, calendar}
- **attachments**(id, session_id, path, meta_json)
- **indexes**: for embeddings and fast lookup (use sqlite-vss or keep FAISS files per session)