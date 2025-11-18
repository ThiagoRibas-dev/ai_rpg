import logging
from typing import Any, Dict, Optional
from app.setup.setup_manifest import SetupManifest
from app.models.stat_block import AbilityDef, VitalDef, TrackDef
from app.tools.builtin._state_storage import get_entity, set_entity

logger = logging.getLogger(__name__)

def handler(
    property_name: str,
    description: str,
    template: Optional[str] = "stat", # Default to stat
    default_value: Any = 10,
    min_value: Optional[int] = 0,
    max_value: Optional[int] = 20,
    **context: Any,
) -> Dict[str, Any]:
    """
    Updates the StatBlockTemplate to include a new property.
    Maps generic requests to specific StatBlock definitions (Abilities, Vitals, Tracks).
    """
    session_id = context.get("session_id")
    db = context.get("db_manager")

    if not session_id or not db:
        return {"success": False, "error": "Missing session context."}

    # 1. Get the active template
    manifest = SetupManifest(db).get_manifest(session_id)
    template_id = manifest.get("stat_template_id")
    
    if not template_id:
        return {"success": False, "error": "No active StatBlockTemplate found. Please generate the template from rules first."}

    stat_template = db.stat_templates.get_by_id(template_id)
    if not stat_template:
        return {"success": False, "error": "StatBlockTemplate not found in DB."}

    category_added = "unknown"

    # 2. Map "Template" to Schema Type
    # This logic translates user/AI intent into our strict schema
    
    if template in ["stat", "attribute", "integer"]:
        # Add as Ability
        new_def = AbilityDef(
            name=property_name,
            description=description,
            data_type="integer",
            default=default_value,
            range_min=min_value,
            range_max=max_value
        )
        # Remove existing if same name
        stat_template.abilities = [x for x in stat_template.abilities if x.name != property_name]
        stat_template.abilities.append(new_def)
        category_added = "abilities"

    elif template in ["resource", "vital"]:
        # Add as Vital
        new_def = VitalDef(
            name=property_name,
            description=description,
            min_value=min_value or 0,
            has_max=True # Assume max for resources
        )
        stat_template.vitals = [x for x in stat_template.vitals if x.name != property_name]
        stat_template.vitals.append(new_def)
        category_added = "vitals"
        
    elif template in ["flag", "reputation", "tracker", "clock"]:
        # Add as Track
        style = "clock" if template == "clock" else "bar"
        if template == "flag":
            style = "checkboxes"
        
        new_def = TrackDef(
            name=property_name,
            description=description,
            max_value=max_value or 4,
            visual_style=style
        )
        stat_template.tracks = [x for x in stat_template.tracks if x.name != property_name]
        stat_template.tracks.append(new_def)
        category_added = "tracks"
        
    else:
        # Fallback: Add as Ability (String/Misc)
        new_def = AbilityDef(
            name=property_name,
            description=description,
            data_type="integer", # Defaulting to integer for safety
            default=default_value
        )
        stat_template.abilities = [x for x in stat_template.abilities if x.name != property_name]
        stat_template.abilities.append(new_def)
        category_added = "abilities"

    # 3. Save Template
    db.stat_templates.update(template_id, stat_template)

    # 4. Backfill Player Entity
    # We need to ensure the current player object has a default value for this new key
    player = get_entity(session_id, db, "character", "player")
    if player:
        if category_added == "abilities":
            player.setdefault("abilities", {})[property_name] = default_value
        elif category_added == "vitals":
            # Vitals need {current, max} structure
            player.setdefault("vitals", {})[property_name] = {"current": default_value, "max": default_value}
        elif category_added == "tracks":
            player.setdefault("tracks", {})[property_name] = 0
            
        set_entity(session_id, db, "character", "player", player)

    logger.info(f"Upserted '{property_name}' into {category_added} of template {template_id}")
    return {
        "success": True, 
        "property": property_name, 
        "category": category_added,
        "note": "Player entity updated with default value."
    }
