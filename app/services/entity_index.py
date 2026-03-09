"""
Entity Index Service
Maintains a lightweight registry of all known world entities in game_state.
Injected into the system prompt so the LLM knows what exists.
"""

import logging

from app.models.vocabulary import MemoryKind
from app.services.state_service import get_entity, set_entity
from app.tools.schemas import StateQuery, ContextRetrieve

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


def render_index(index: dict) -> str:
    """Format the index as a compact markdown block for prompt injection."""
    # Instead of a hardcoded string with the name of the tool, we directly reference the tool names via the schema classes
    lines = ["# WORLD INDEX", f"Use `{StateQuery.model_fields['name'].default}` or `{ContextRetrieve.model_fields['name'].default}` to look up details.\n"]

    # Locations
    locs = index.get("locations", {})
    if locs:
        lines.append(f"**Locations** ({len(locs)}):")
        for key, desc in locs.items():
            lines.append(f"  - `{key}`: {desc}")

    # NPCs
    npcs = index.get("npcs", {})
    if npcs:
        lines.append(f"**NPCs** ({len(npcs)}):")
        for key, desc in npcs.items():
            lines.append(f"  - `{key}`: {desc}")

    # Memory kinds
    for kind in MemoryKind:
        entries = index.get(kind.value, [])
        if entries:
            lines.append(f"**{kind.value.title()}** ({len(entries)}):")
            for title in entries:
                lines.append(f"  - {title}")

    return "\n".join(lines)
