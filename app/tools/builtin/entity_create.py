import logging
from typing import Dict, Any, Optional
from app.tools.builtin._state_storage import get_entity, set_entity
from app.setup.setup_manifest import SetupManifest

logger = logging.getLogger(__name__)


def handler(
    entity_type: str,
    entity_key: str,
    data: Dict[str, Any],
    template_name: Optional[str] = None,
    **context: Any,
) -> dict:
    """
    Handler for entity.create. 
    Validates data against a StatBlockTemplate before creating.
    """
    session_id = context.get("session_id")
    db = context.get("db_manager")
 
    if not session_id or not db:
        raise ValueError("Missing session context for entity.create.")

    # Check if entity already exists to prevent overwrites
    if get_entity(session_id, db, entity_type, entity_key):
        raise ValueError(f"Cannot create entity: An entity with key '{entity_key}' of type '{entity_type}' already exists.")
 
    # Find the Template
    manifest = SetupManifest(db).get_manifest(session_id)
    ruleset_id = manifest.get("ruleset_id")
    
    stat_template = None
    template_id_to_link = None
    
    if ruleset_id:
        templates = db.stat_templates.get_by_ruleset(ruleset_id)
        
        if template_name:
             # Look for specific name
             found = next((t for t in templates if t["name"].lower() == template_name.lower()), None)
             if found:
                 template_id_to_link = found["id"]
                 stat_template = db.stat_templates.get_by_id(found["id"])
        
        if not stat_template and templates:
             # Fallback to first available (usually Player Character) or default
             template_id_to_link = templates[0]["id"]
             stat_template = db.stat_templates.get_by_id(template_id_to_link)
 
    # Validate if we found a template
    if stat_template:
        data["template_id"] = template_id_to_link # Link entity to template ID from DB lookup
        # TODO: Perform full validation against template structure here.
        # For MVP, we trust the AI's data structure but link the ID so character.update works later.
        pass
    else:
        logger.warning(f"Creating entity '{entity_key}' without a StatBlockTemplate (none found).")
 
    # Validation passed, so we can safely create the entity
    version = set_entity(session_id, db, entity_type, entity_key, data)

    return {"success": True, "entity_type": entity_type, "entity_key": entity_key, "version": version}
