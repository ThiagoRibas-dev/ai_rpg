You're absolutely right! Let me revise the TODO to remove Phase 7 and add full CRUD tools in Phase 2.

# V4 TODO: Simple Agentic Memory

This document outlines the development tasks for implementing a persistent, agentic memory system that allows the LLM to autonomously manage and retrieve important information from conversations.

---

## Phase 1: Memory Storage Backend

**Goal:** Upgrade the memory storage from the current in-memory dictionary to a persistent, queryable system.

### Database Schema

-   [x] **Extend Database Schema (`db_manager.py`):**
    -   [x] Create `memories` table with fields:
        -   `id` (INTEGER PRIMARY KEY)
        -   `session_id` (INTEGER, FOREIGN KEY to sessions)
        -   `kind` (TEXT) - "episodic", "semantic", "lore", "user_pref"
        -   `content` (TEXT) - the memory content
        -   `priority` (INTEGER) - 1-5 importance rating
        -   `tags` (TEXT) - JSON array of tags
        -   `created_at` (TIMESTAMP)
        -   `last_accessed` (TIMESTAMP)
        -   `access_count` (INTEGER) - how many times retrieved

-   [x] **Implement Memory CRUD Methods:**
    -   [x] `create_memory(session_id, kind, content, priority, tags)` -> Memory
    -   [x] `get_memories_by_session(session_id)` -> List[Memory]
    -   [x] `query_memories(session_id, kind=None, tags=None, limit=10)` -> List[Memory]
    -   [x] `update_memory_access(memory_id)` -> increments access_count and updates last_accessed
    -   [x] `update_memory(memory_id, content=None, priority=None, tags=None)` -> Memory
    -   [x] `delete_memory(memory_id)`

### Data Models

-   [x] **Create Memory Model (`app/models/memory.py`):**
    -   [x] Define `Memory` dataclass with all fields from the schema
    -   [x] Add helper methods for serialization if needed

---

## Phase 2: Memory Tools - Full CRUD

**Goal:** Provide the LLM with complete control over memory management through tools.

### Refactor `memory.upsert`

-   [x] **Update `memory_upsert.py`:**
    -   [x] Remove the in-memory `_MEM` dictionary
    -   [x] Modify handler to accept a `session_id` parameter (from orchestrator context)
    -   [x] Call `db_manager.create_memory()` to persist the memory
    -   [x] Return memory ID and confirmation

-   [x] **Update Tool Schema in `schemas.py`:**
    -   [x] Ensure `MemoryUpsert` Pydantic model matches the new implementation
    -   [x] Add validation for kind enum values
    -   [x] Add validation for priority range (1-5)

### Create `memory.query` Tool

-   [x] **Create `memory_query.py` (`app/tools/builtin/`):**
    -   [x] Define schema with parameters:
        -   `kind` (optional) - filter by memory type
        -   `tags` (optional) - filter by tags (any match)
        -   `query_text` (optional) - simple text search in content
        -   `limit` (optional, default 5) - max results to return
    -   [x] Implement handler that:
        -   Accepts `session_id` from orchestrator
        -   Calls `db_manager.query_memories()`
        -   Updates `last_accessed` and `access_count` for retrieved memories
        -   Returns list of matching memories with metadata (id, kind, content, priority, tags)

-   [x] **Add Schema Model (`app/tools/schemas.py`):**
    -   [x] Create `MemoryQuery` Pydantic model matching the schema
    -   [x] Add to `_TOOL_SCHEMA_MAP` in `registry.py`

### Create `memory.update` Tool

-   [x] **Create `memory_update.py` (`app/tools/builtin/`):**
    -   [x] Define schema with parameters:
        -   `memory_id` (required) - ID of memory to update
        -   `content` (optional) - new content
        -   `priority` (optional) - new priority (1-5)
        -   `tags` (optional) - new tags array
    -   [x] Implement handler that:
        -   Accepts `session_id` for validation
        -   Calls `db_manager.update_memory()`
        -   Returns confirmation with updated memory

-   [x] **Add Schema Model (`app/tools/schemas.py`):**
    -   [x] Create `MemoryUpdate` Pydantic model
    -   [x] Add to `_TOOL_SCHEMA_MAP` in `registry.py`

### Create `memory.delete` Tool

-   [x] **Create `memory_delete.py` (`app/tools/builtin/`):**
    -   [x] Define schema with parameters:
        -   `memory_id` (required) - ID of memory to delete
    -   [x] Implement handler that:
        -   Accepts `session_id` for validation (ensure memory belongs to session)
        -   Calls `db_manager.delete_memory()`
        -   Returns confirmation

-   [x] **Add Schema Model (`app/tools/schemas.py`):**
    -   [x] Create `MemoryDelete` Pydantic model
    -   [x] Add to `_TOOL_SCHEMA_MAP` in `registry.py`

### Orchestrator Integration

-   [x] **Modify Orchestrator (`orchestrator.py`):**
    -   [x] Pass `session_id` context to tool execution
    -   [x] Update tool execution to include current session context

-   [x] **Update Tool Registry (`registry.py`):**
    -   [x] Modify `execute_tool()` to accept optional `context: Dict[str, Any]` parameter
    -   [x] Pass context through to tool handlers that need it
    -   [x] Update the tool handler signature to accept context as needed

---

## Phase 3: Memory Retrieval in Context Assembly

**Goal:** Automatically inject relevant memories into the LLM's context during each turn.

### Automatic Memory Injection

-   [x] **Extend `_assemble_context()` in Orchestrator:**
    -   [x] Add a new step before World Info: retrieve relevant memories
    -   [x] Query memories with:
        -   Recent message keywords (simple keyword extraction)
        -   Priority >= 3 (important memories always included)
        -   Limit to top 5-10 to avoid context bloat
    -   [x] Format memories as a new context section:
        ```
        === RELEVANT MEMORIES ===
        [Episodic] (Priority 5, ID: 42): The player saved the village elder from bandits.
        [Semantic] (Priority 4, ID: 13): Fire spells are ineffective against ice elementals.
        ```
    -   [x] Include memory IDs so the LLM can reference them in update/delete tools

-   [x] **Memory Ranking Algorithm:**
    -   [x] Simple keyword matching: count keyword overlaps with recent messages
    -   [x] Weight by priority (priority 5 memories should appear even with fewer keyword matches)
    -   [x] Recency bias: newer memories slightly preferred over old ones (optional)
    -   [x] Always include priority 5 memories regardless of keywords

### Memory Consolidation

-   [x] **Instruct the LLM to Manage Memories:**
    -   [x] Update system prompts to encourage the LLM to:
        -   Update existing memories when new information contradicts or expands them
        -   Delete outdated or incorrect memories
        -   Merge redundant memories
        -   Increase priority of frequently relevant information
        -   Decrease priority of rarely used information

---

## Phase 4: GUI - Memory Inspector

**Goal:** Add a user-facing panel to view, search, and manage the AI-generated memories.

### Memory Panel UI

-   [x] **Add "Memories" Tab to Game State Inspector:**
    -   [x] Add a new tab: `self.game_state_inspector_tabs.add("Memories")`
    -   [x] Create the memory display layout

-   [x] **Memory List View:**
    -   [x] Create a scrollable frame showing all memories for the current session
    -   [x] Display each memory as a card/frame with:
        -   Memory ID (small, top-right corner)
        -   Kind badge (colored: episodic=blue, semantic=green, lore=purple, user_pref=orange)
        -   Priority stars (★★★★★)
        -   Content preview (first 100 chars, expandable)
        -   Tags as small pills/badges
        -   Created date
        -   Access count (how many times LLM retrieved it)

-   [x] **Memory Filtering:**
    -   [x] Add dropdown to filter by kind (All, Episodic, Semantic, Lore, User Pref)
    -   [x] Add search box to filter by content/tags
    -   [x] Add sort options: by date (newest/oldest), by priority, by access count

-   [x] **Memory Detail View:**
    -   [x] Clicking a memory opens a detail panel or popup
    -   [x] Show full content, all tags, metadata (ID, created, last accessed, access count)
    -   [x] Add "Edit" button to manually modify content, priority, or tags
    -   [x] Add "Delete" button with confirmation
    -   [x] Manual edits save directly to database (not via tools)

### Memory Management Actions

-   [x] **Add Memory Management Buttons:**
    -   [x] "Refresh" - reload memories from database
    -   [x] "New Memory" - manually create a memory (user-created, not AI)
    -   [x] "Clear All Memories" - delete all memories for session (with confirmation)
    -   [x] "Export Memories" - save as JSON file
    -   [x] "Import Memories" - load from JSON file

-   [x] **Real-time Updates:**
    -   [x] After each turn, refresh the memory list automatically
    -   [x] Highlight newly created memories (flash animation or "NEW" badge)
    -   [x] Highlight updated memories (different color badge)
    -   [x] Show deleted memories with strikethrough animation before removing
    -   [x] Show a notification when memories are created/updated/deleted

---

## Phase 5: Memory Analytics & Insights

**Goal:** Provide insights into how the AI is using memory, helping users understand the system's behavior.

### Memory Statistics

-   [x] **Add Statistics Panel:**
    -   [x] Total memories by kind (pie chart or simple counts)
    -   [x] Most accessed memories (top 5)
    -   [x] Most recently created memories (last 5)
    -   [x] Memory activity: created/updated/deleted this session

-   [x] **Memory Health Indicators:**
    -   [x] Warn if too many low-priority memories (suggests noise)
    -   [x] Warn if too few memories (AI might not be remembering enough)
    -   [x] Show which memories were auto-injected in the last turn

### Memory Visualization

-   [x] **Tag Cloud (Optional):**
    -   [x] Display frequently used tags as a word cloud
    -   [x] Clicking a tag filters memories by that tag

-   [x] **Timeline View (Optional):**
    -   [x] Show memories on a chronological timeline
    -   [x] Useful for episodic memories to see story progression

---

## Phase 6: Performance Optimization & Refinements

**Goal:** Ensure the memory system is reliable and performs well.

### Performance Optimization

-   [x] **Add Indexing:**
    -   [x] Add database index on `session_id` for faster queries
    -   [x] Add index on `kind` for filtered queries
    -   [x] Add index on `priority` for sorted queries
    -   [x] Consider full-text search index on `content` (SQLite FTS5) if needed

### User Experience Polish

-   [x] **Add Tooltips:**
    -   [x] Explain what each memory kind means
    -   [x] Explain priority levels (1 = trivial, 5 = critical)
    -   [x] Explain how memories are automatically retrieved
    -   [x] Show memory ID and explain that AI uses it to update/delete

-   [x] **Tutorial/Guide:**
    -   [x] Add a "How Memory Works" info button in the Memory tab
    -   [x] Show example memories on first run
    -   [x] Add tips for effective memory usage
    -   [x] Explain that AI can create, update, and delete memories autonomously

-   [x] **Prompt Engineering:**
    -   [x] Update planning and narrative templates to encourage memory usage
    -   [x] Add examples of when to create/update/delete memories
    -   [x] Encourage the AI to query memories before making important decisions

---

## Success Criteria

By the end of v4, the system should:

-   ✅ Allow the LLM to autonomously create, query, update, and delete memories
-   ✅ Persist memories between sessions in the database
-   ✅ Display memories in a user-friendly GUI panel
-   ✅ Automatically inject relevant memories into the LLM's context
-   ✅ Provide transparency into what the AI is remembering
-   ✅ Enable users to view, search, manually edit, and delete memories
-   ✅ Show real-time updates when the AI modifies memories
-   ✅ Allow export/import of memories for backup or sharing

---

## Notes

- Keep it simple: v4 is "Simple Agentic Memory", not a complex RAG system (that's v5)
- The AI should be trusted to manage its own memories, but users can override
- Focus on transparency: users should see all memory operations in real-time
- Memory retrieval should be fast and not bloat the context
- Consider adding a setting to enable/disable automatic memory injection
- The LLM should be encouraged (via prompts) to actively maintain memory hygiene