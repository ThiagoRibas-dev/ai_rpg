"""
State storage layer using dedicated SQL table.
Provides session-scoped entity management with versioning.
Refactored from app.tools.builtin._state_storage.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def get_entity(
    session_id: int, db_manager, entity_type: str, key: str
) -> Dict[str, Any]:
    """Get a single entity."""
    if not session_id or not db_manager:
        raise ValueError("Missing session_id or db_manager")
    try:
        return db_manager.game_state.get_entity(session_id, entity_type, key)
    except Exception as e:
        logger.error(f"Error loading entity {entity_type}:{key}: {e}")
        return {}


def set_entity(
    session_id: int, db_manager, entity_type: str, key: str, value: Dict[str, Any]
) -> int:
    """Set/update a single entity. Returns version."""
    if not session_id or not db_manager:
        raise ValueError("Missing session_id or db_manager")
    try:
        version = db_manager.game_state.set_entity(session_id, entity_type, key, value)
        logger.debug(f"Updated {entity_type}:{key} to version {version}")
        return version
    except Exception as e:
        logger.error(f"Error saving entity {entity_type}:{key}: {e}")
        raise


def get_all_of_type(session_id: int, db_manager, entity_type: str) -> Dict[str, Any]:
    """Get all entities of a specific type."""
    if not session_id or not db_manager:
        raise ValueError("Missing session_id or db_manager")
    try:
        return db_manager.game_state.get_all_entities_by_type(session_id, entity_type)
    except Exception as e:
        logger.error(f"Error loading entities of type {entity_type}: {e}")
        return {}


def get_versions(session_id: int, db_manager, entity_type: str) -> Dict[str, int]:
    """
    Get version map for cache invalidation. 
    Returns: {'key': version_int}
    """
    if not session_id or not db_manager:
        return {}
    try:
        return db_manager.game_state.get_versions(session_id, entity_type)
    except Exception as e:
        logger.error(f"Error fetching versions for {entity_type}: {e}")
        return {}


def delete_entity(session_id: int, db_manager, entity_type: str, key: str):
    """Delete a specific entity."""
    if not session_id or not db_manager:
        raise ValueError("Missing session_id or db_manager")
    try:
        db_manager.game_state.delete_entity(session_id, entity_type, key)
        logger.debug(f"Deleted {entity_type}:{key}")
    except Exception as e:
        logger.error(f"Error deleting entity {entity_type}:{key}: {e}")
        raise