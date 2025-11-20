from typing import Any, Optional
from app.tools.builtin._state_storage import get_entity, set_entity
from app.tools.builtin.scene_add_member import handler as scene_add_member

def handler(
    key: str,
    name_display: str,
    visual_description: str,
    stat_template: str,
    initial_disposition: str = "neutral",
    location_key: Optional[str] = None,
    **context: Any
) -> dict:
    """
    Handler for npc.spawn.
    Creates an entity, links it to a template, and adds it to the active scene.
    """
    session_id = context["session_id"]
    db = context["db_manager"]

    # 1. Check for duplicates
    if get_entity(session_id, db, "character", key):
        return {"success": False, "error": f"Character key '{key}' already exists."}

    # 2. Resolve Location
    if not location_key:
        scene = get_entity(session_id, db, "scene", "active_scene")
        location_key = scene.get("location_key") if scene else None
    
    if not location_key:
        return {"success": False, "error": "Cannot spawn NPC: No location specified and no active scene location found."}

    # 3. Resolve Template
    # We need to find the template ID based on the name provided (e.g., "Goblin")
    # This requires scanning templates linked to the session's ruleset.
    from app.setup.setup_manifest import SetupManifest
    manifest = SetupManifest(db).get_manifest(session_id)
    ruleset_id = manifest.get("ruleset_id")
    
    template_id = None
    if ruleset_id:
        templates = db.stat_templates.get_by_ruleset(ruleset_id)
        found = next((t for t in templates if t["name"].lower() == stat_template.lower()), None)
        if found:
            template_id = found["id"]
    
    # 4. Initialize Entity Structure
    # (Minimal scaffolding, real stats would be populated by a subsequent update or defaults)
    npc_data = {
        "name": name_display,
        "description": visual_description,
        "template_id": template_id,
        "location_key": location_key,
        "disposition": initial_disposition,
        "abilities": {},
        "vitals": {}, # Template defaults will be assumed by UI if missing
        "inventory": []
    }

    # 5. Save Entity
    set_entity(session_id, db, "character", key, npc_data)

    # 6. Add to Active Scene
    # We call the existing tool handler to ensure consistency
    scene_result = scene_add_member(key, **context)
    
    # 7. Initialize NPC Profile (The Brain)
    # Required for JIT Simulation
    npc_profile = {
        "personality_traits": context.get("personality_traits", []), # Not passed by schema yet, default empty
        "motivations": ["Survive"],
        "directive": "idle",
        "knowledge_tags": [],
        "relationships": {},
        "last_updated_time": context.get("current_game_time", "Day 1, Dawn")
    }
    # Attempt to parse description for traits? (Optional polish)
    
    set_entity(session_id, db, "npc_profile", key, npc_profile)

    return {
        "success": True,
        "key": key,
        "name": name_display,
        "location": location_key,
        "template_found": template_id is not None,
        "scene_updated": scene_result.get("success", False)
    }
