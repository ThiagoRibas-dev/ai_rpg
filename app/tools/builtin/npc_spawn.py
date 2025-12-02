from typing import Any, Optional
from app.services.state_service import get_entity, set_entity

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
        return {"success": False, "error": "Cannot spawn NPC: No location specified and no active scene."}

    # 3. Resolve Template
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
    npc_data = {
        "name": name_display,
        "description": visual_description,
        "template_id": template_id,
        "location_key": location_key,
        "disposition": initial_disposition,
        "abilities": {},
        "vitals": {},
        "inventory": []
    }

    set_entity(session_id, db, "character", key, npc_data)

    # 5. Add to Active Scene (Logic Inlined from scene_add_member)
    scene = get_entity(session_id, db, "scene", "active_scene")
    if not scene:
        scene = {
            "location_key": location_key,
            "members": ["character:player"],
            "state_tags": []
        }

    member_id = f"character:{key}"
    if member_id not in scene.get("members", []):
        scene.setdefault("members", []).append(member_id)
        set_entity(session_id, db, "scene", "active_scene", scene)
    
    # 6. Initialize NPC Profile
    npc_profile = {
        "personality_traits": context.get("personality_traits", []),
        "motivations": ["Survive"],
        "directive": "idle",
        "knowledge_tags": [],
        "relationships": {},
        "last_updated_time": context.get("current_game_time", "Day 1, Dawn")
    }
    set_entity(session_id, db, "npc_profile", key, npc_profile)

    return {
        "success": True,
        "key": key,
        "name": name_display,
        "location": location_key
    }
