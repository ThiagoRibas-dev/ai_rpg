"""
Entity Index Service
Maintains a lightweight registry of all known world entities in game_state.
Injected into the system prompt so the LLM knows what exists.
"""

import logging

from app.models.vocabulary import MemoryKind
from app.services.state_service import get_entity, set_entity
from app.tools.schemas import ContextRetrieve, StateQuery

logger = logging.getLogger(__name__)

INDEX_ENTITY_TYPE = "index"
INDEX_ENTITY_KEY = "world_index"


def _ensure_index(session_id: int, db) -> dict:
    """Load or create the world index with all expected keys."""
    index = get_entity(session_id, db, INDEX_ENTITY_TYPE, INDEX_ENTITY_KEY)
    if index:
        return index

    # Initialize with fixed + dynamic keys
    index = {
        "locations": {},
        "npcs": {},
    }
    for kind in MemoryKind:
        index[kind.value] = []

    set_entity(session_id, db, INDEX_ENTITY_TYPE, INDEX_ENTITY_KEY, index)
    return index


def get_index(session_id: int, db) -> dict:
    """Read the current world index."""
    return _ensure_index(session_id, db)


def _save_index(session_id: int, db, index: dict):
    """Persist the index back to game_state."""
    set_entity(session_id, db, INDEX_ENTITY_TYPE, INDEX_ENTITY_KEY, index)


def add_location(session_id: int, db, key: str, one_liner: str):
    """Register a location in the index."""
    index = _ensure_index(session_id, db)
    index["locations"][key] = one_liner
    _save_index(session_id, db, index)


def add_npc(session_id: int, db, key: str, one_liner: str):
    """Register an NPC in the index."""
    index = _ensure_index(session_id, db)
    index["npcs"][key] = one_liner
    _save_index(session_id, db, index)


def add_memory(session_id: int, db, kind: str, title: str):
    """Register a memory title in the index under its MemoryKind key."""
    index = _ensure_index(session_id, db)
    kind_key = kind if isinstance(kind, str) else kind.value
    if kind_key not in index:
        index[kind_key] = []
    if title not in index[kind_key]:
        index[kind_key].append(title)
    _save_index(session_id, db, index)


def remove_entry(session_id: int, db, category: str, key: str):
    """Remove an entry from the index."""
    index = _ensure_index(session_id, db)
    if category in ("locations", "npcs"):
        index.get(category, {}).pop(key, None)
    else:
        lst = index.get(category, [])
        if key in lst:
            lst.remove(key)
    _save_index(session_id, db, index)


def smart_truncate(text: str, max_len: int = 90) -> str:
    """
    Truncates text to a max length, but tries to break at a sentence or word boundary.
    Logic:
    1. Truncate to max_len chars.
    2. Find last period, comma, or space within that subset.
    3. Return truncated text with ellipsis.
    """
    if len(text) <= max_len:
        return text

    # Initial truncation
    subset = text[:max_len]

    # Look for last period, comma, or space
    last_idx = -1
    for char in (".", ",", " "):
        idx = subset.rfind(char)
        last_idx = max(last_idx, idx)

    if last_idx > 0:
        # Return truncated text stripped of the separator, plus ellipsis
        return subset[:last_idx].rstrip("., ") + "..."

    # Fallback to hard truncation if no boundary found
    return subset + "..."


def render_index(index: dict) -> str:
    """Format the index as a compact markdown block for prompt injection."""
    lines = [
        f"Use `{StateQuery.model_fields['name'].default}` or `{ContextRetrieve.model_fields['name'].default}` to look up full details.\n"
    ]

    table_rows = []

    # 1. Locations
    for key, desc in index.get("locations", {}).items():
        summary = smart_truncate(desc)
        table_rows.append(f"| Location | `{key}` | {summary} |")

    # 2. NPCs
    for key, desc in index.get("npcs", {}).items():
        summary = smart_truncate(desc)
        table_rows.append(f"| NPC | `{key}` | {summary} |")

    # 3. Memories (Lore, Rules, etc.)
    for kind in MemoryKind:
        entries = index.get(kind.value, [])
        for title in entries:
            summary = smart_truncate(title)
            table_rows.append(f"| {kind.value.title()} | - | {summary} |")

    if table_rows:
        lines.append("| Type | Entity ID | Summary |")
        lines.append("| :--- | :--- | :--- |")
        lines.extend(table_rows)

    return "\n".join(lines)
