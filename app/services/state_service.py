import logging
from typing import TYPE_CHECKING, Any, cast

from app.models.vocabulary import EntityType

if TYPE_CHECKING:
    from app.database.db_manager import DBManager

logger = logging.getLogger(__name__)


def get_entity(
    session_id: int, db_manager: "DBManager", entity_type: str | EntityType, key: str
) -> dict[str, Any]:
    """Get a single entity."""
    if not session_id or not db_manager:
        raise ValueError("Missing session_id or db_manager")
    try:
        if not db_manager.game_state:
            return {}
        data = db_manager.game_state.get_entity(session_id, str(entity_type), key)
        return cast(dict[str, Any], data)
    except Exception as e:
        logger.error(f"Error loading entity {entity_type}:{key}: {e}")
        return {}



def set_entity(
    session_id: int, db_manager, entity_type: str, key: str, value: dict[str, Any]
) -> int:
    """Set/update a single entity. Returns version."""
    if not session_id or not db_manager:
        raise ValueError("Missing session_id or db_manager")
    try:
        if not db_manager.game_state:
            raise ValueError("GameStateRepository not initialized")
        version = db_manager.game_state.set_entity(
            session_id, str(entity_type), key, value
        )
        logger.debug(f"Updated {entity_type}:{key} to version {version}")
        return cast(int, version)
    except Exception as e:
        logger.error(f"Error saving entity {entity_type}:{key}: {e}")
        raise



def get_all_of_type(session_id: int, db_manager: "DBManager", entity_type: str | EntityType) -> dict[str, Any]:
    """Get all entities of a specific type."""
    if not session_id or not db_manager:
        raise ValueError("Missing session_id or db_manager")
    try:
        if not db_manager.game_state:
            return {}
        data = db_manager.game_state.get_all_entities_by_type(
            session_id, str(entity_type)
        )
        return cast(dict[str, Any], data)
    except Exception as e:
        logger.error(f"Error loading entities of type {entity_type}: {e}")
        return {}



def get_versions(session_id: int, db_manager: "DBManager", entity_type: str | EntityType) -> dict[str, int]:
    """
    Get version map for cache invalidation.
    Returns: {'key': version_int}
    """
    if not session_id or not db_manager:
        return {}
    try:
        if not db_manager.game_state:
            return {}
        data = db_manager.game_state.get_versions(session_id, str(entity_type))
        return cast(dict[str, int], data)
    except Exception as e:
        logger.error(f"Error fetching versions for {entity_type}: {e}")
        return {}



def delete_entity(session_id: int, db_manager, entity_type: str, key: str):
    """Delete a specific entity."""
    if not session_id or not db_manager:
        raise ValueError("Missing session_id or db_manager")
    try:
        if not db_manager.game_state:
            raise ValueError("GameStateRepository not initialized")
        db_manager.game_state.delete_entity(session_id, str(entity_type), key)
        logger.debug(f"Deleted {entity_type}:{key}")
    except Exception as e:
        logger.error(f"Error deleting entity {entity_type}:{key}: {e}")
        raise

