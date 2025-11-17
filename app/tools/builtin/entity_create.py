import logging
from typing import Dict, Any
from app.tools.builtin._state_storage import get_entity, set_entity
from app.utils.state_validator import StateValidator, ValidationError

logger = logging.getLogger(__name__)


def handler(
    entity_type: str,
    entity_key: str,
    data: Dict[str, Any],
    **context: Any,
) -> dict:
    """
    Handler for entity.create. It validates the provided data against the
    session manifest before creating the new entity in the game state.
    """
    session_id = context.get("session_id")
    db = context.get("db_manager")
    manifest = context.get("manifest") # Manifest is passed in via TurnManager/ToolExecutor

    if not session_id or not db or not manifest:
        raise ValueError("Missing session context or manifest for entity.create.")

    # Check if entity already exists to prevent overwrites
    if get_entity(session_id, db, entity_type, entity_key):
        raise ValueError(f"Cannot create entity: An entity with key '{entity_key}' of type '{entity_type}' already exists.")

    # Validate the data against the manifest's schema
    try:
        validator = StateValidator(manifest)
        validator.validate_entity(entity_type, data)
        logger.debug(f"Validation PASSED for new entity '{entity_key}'.")
    except ValidationError as e:
        logger.warning(f"AI failed to create a valid entity '{entity_key}': {e}")
        raise  # Re-raise the validation error to be sent back to the AI

    # Validation passed, so we can safely create the entity
    version = set_entity(session_id, db, entity_type, entity_key, data)

    return {"success": True, "entity_type": entity_type, "entity_key": entity_key, "version": version}
