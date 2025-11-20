import logging
from typing import Any, Dict, List

from app.tools.builtin._state_storage import get_entity, set_entity
from app.utils.state_validator import StateValidator
from app.utils.math_engine import recalculate_derived_stats

logger = logging.getLogger(__name__)

def handler(character_key: str, updates: List[Dict[str, Any]], **context) -> dict:
    """
    Handler for the character.update tool.
    Updates character abilities, vitals, or tracks using the StatBlockTemplate for validation.
    """
    session_id = context["session_id"]
    db = context["db_manager"]
    
    # PHASE 1 SAFETY CHECK: Restrict direct updates during gameplay
    # The AI must use specific tools like 'apply_damage', 'inventory.add', etc.
    # This prevents the AI from bypassing game rules or hallucinating math.
    # We check if the session object (passed in context via executor) has game_mode set.
    # Note: The ToolExecutor puts the *session object* into context? No, usually just IDs.
    # We need to check how Executor builds context. It passes 'manifest'.
    if context.get("manifest", {}).get("ready_to_play") is True:
         raise ValueError("character.update is disabled during GAMEPLAY. Use specific tools like 'character.apply_damage' or 'inventory.add_item'.")

    # 1. Load Entity
    entity = get_entity(session_id, db, "character", character_key)
    if not entity:
        raise ValueError(f"Character '{character_key}' not found.")

    # 2. Load Template
    # Fallback: if entity has no template_id, we might be in early setup or legacy mode.
    # Ideally, we fetch the default template for the ruleset.
    template_id = entity.get("template_id")
    if not template_id:
         # Try to fetch any template for the session's ruleset? 
         # For MVP, assume we must have one.
         # In a real scenario, we might fetch the 'default' template from the DB.
         # Assuming the orchestrator or setup ensured this.
         # Let's look for *any* template linked to the session's ruleset if possible, 
         # but for now, we'll rely on 'manifest' context or explicit ID.
         
         # HACK: If 'manifest' is in context (passed by Executor), use that? 
         # But 'manifest' is now just IDs.
         # We will proceed optimistically or fail.
         pass
         
    if template_id:
        stat_template = db.stat_templates.get_by_id(template_id)
    else:
        # Fallback for robustness: Check if a validator is already in context (ToolExecutor might put it there)
        # This supports the transition phase.
        stat_template = context.get("stat_template")
    
    if not stat_template:
        raise ValueError(f"No StatBlockTemplate found for character '{character_key}'.")

    # 3. Validate & Apply Updates
    validator = StateValidator(stat_template)
    derived_stats_keys = {d.name for d in stat_template.derived_stats}
    
    updated_keys = []
    for update_pair in updates:
        key = update_pair["key"]
        value = update_pair["value"]

        # Safety: Prevent AI from overwriting Derived Stats directly
        if key in derived_stats_keys:
            logger.warning(f"Ignored direct update to derived stat '{key}'. AI should update base abilities instead.")
            continue
        
        category = validator.validate_update(key, value)
        
        # Determine where to store it in the dict structure
        # Structure: entity = { "abilities": {...}, "vitals": {...}, "tracks": {...} }
        if category == "ability":
            entity.setdefault("abilities", {})[key] = value
        elif category == "vital":
             # Vitals are complex objects {current, max}
             # Check if this vital has a max_formula
             vital_def = next((v for v in stat_template.vitals if v.name == key), None)
             has_formula = vital_def and vital_def.max_formula

             # If value is int, assume 'current'
             if isinstance(value, (int, float)):
                 current_vital = entity.setdefault("vitals", {}).get(key, {})
                 current_vital["current"] = value
                 entity["vitals"][key] = current_vital
             else:
                 # If it's a dict, we might need to filter out 'max' if it's calculated
                 if has_formula and isinstance(value, dict) and "max" in value:
                     logger.info(f"Ignoring manual max update for '{key}' due to formula.")
                     value.pop("max")
                     # Merge with existing to preserve current if not sent, or update current
                     current_vital = entity.setdefault("vitals", {}).get(key, {})
                     current_vital.update(value)
                     entity["vitals"][key] = current_vital
                 else:
                     entity.setdefault("vitals", {})[key] = value
        elif category == "track":
            # Tracks can be simple integers (0) or objects {value: 0, max: 4}
            if isinstance(value, int):
                current_track = entity.setdefault("tracks", {}).get(key)
                
                # If it's already a dict, update the value field
                if isinstance(current_track, dict):
                    current_track["value"] = value
                    entity["tracks"][key] = current_track
                else:
                    # Otherwise (it's an int or None), just set the int
                    entity["tracks"][key] = value
            else:
                entity.setdefault("tracks", {})[key] = value
                
        updated_keys.append(key)

    # 4. Recalculate Derived Stats & Formulas
    # This ensures that changing "STR" automatically updates "STR_mod", "AC", "Inventory Cap", etc.
    entity = recalculate_derived_stats(entity, stat_template)

    # 5. Save
    version = set_entity(session_id, db, "character", character_key, entity)

    return {
        "success": True,
        "character_key": character_key,
        "updated_fields": updated_keys,
        "version": version,
    }
