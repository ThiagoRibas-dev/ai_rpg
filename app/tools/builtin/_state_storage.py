"""
State storage layer using dedicated SQL table.
Provides session-scoped entity management with versioning.
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def get_entity(session_id: int, db_manager, entity_type: str, key: str) -> Dict[str, Any]:
    """
    Get a single entity from the game_state table.
    
    Args:
        session_id: Current session ID
        db_manager: Database manager instance
        entity_type: Type of entity (e.g., "character", "inventory", "quest")
        key: Entity key (e.g., "player", "quest_001")
    
    Returns:
        Dictionary containing entity data, or empty dict if not found
    """
    if not session_id or not db_manager:
        raise ValueError("Missing session_id or db_manager")
    
    try:
        return db_manager.get_game_state_entity(session_id, entity_type, key)
    except Exception as e:
        logger.error(f"Error loading entity {entity_type}:{key} for session {session_id}: {e}")
        return {}


def set_entity(session_id: int, db_manager, entity_type: str, key: str, 
               value: Dict[str, Any]) -> int:
    """
    Set/update a single entity in the game_state table.
    
    Args:
        session_id: Current session ID
        db_manager: Database manager instance
        entity_type: Type of entity
        key: Entity key
        value: Entity data as dictionary
    
    Returns:
        Version number after update
    """
    if not session_id or not db_manager:
        raise ValueError("Missing session_id or db_manager")
    
    try:
        version = db_manager.set_game_state_entity(session_id, entity_type, key, value)
        logger.debug(f"Updated {entity_type}:{key} to version {version}")
        return version
    except Exception as e:
        logger.error(f"Error saving entity {entity_type}:{key} for session {session_id}: {e}")
        raise


def get_all_of_type(session_id: int, db_manager, entity_type: str) -> Dict[str, Any]:
    """
    Get all entities of a specific type for a session.
    
    Args:
        session_id: Current session ID
        db_manager: Database manager instance
        entity_type: Type of entity to retrieve
    
    Returns:
        Dictionary mapping entity keys to their data
    """
    if not session_id or not db_manager:
        raise ValueError("Missing session_id or db_manager")
    
    try:
        return db_manager.get_all_entities_by_type(session_id, entity_type)
    except Exception as e:
        logger.error(f"Error loading entities of type {entity_type} for session {session_id}: {e}")
        return {}


def delete_entity(session_id: int, db_manager, entity_type: str, key: str):
    """
    Delete a specific entity.
    
    Args:
        session_id: Current session ID
        db_manager: Database manager instance
        entity_type: Type of entity
        key: Entity key
    """
    if not session_id or not db_manager:
        raise ValueError("Missing session_id or db_manager")
    
    try:
        db_manager.delete_game_state_entity(session_id, entity_type, key)
        logger.debug(f"Deleted {entity_type}:{key}")
    except Exception as e:
        logger.error(f"Error deleting entity {entity_type}:{key}: {e}")
        raise
