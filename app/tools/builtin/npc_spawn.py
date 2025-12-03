from typing import Any, Optional
from app.services.state_service import get_entity, set_entity
from app.setup.setup_manifest import SetupManifest

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
    """
    session_id = context["session_id"]
    db = context["db_manager"]

    if get_entity(session_id, db, "character", key):
        return {"success": False, "error": f"Character key '{key}' already exists."}

    # 1. Resolve Location
    if not location_key:
        scene = get_entity(session_id, db, "scene", "active_scene")
        location_key = scene.get("location_key") if scene else None
    
    if not location_key:
        return {"success": False, "error": "No location specified."}

    # 2. Resolve Template
    # Strategy: Try to find named template. If fail, use the Session Default (Player's) Template.
    manifest = SetupManifest(db).get_manifest(session_id)
    
    template_id = None
    
    # A. Try strict name match
    ruleset_id = manifest.get("ruleset_id")
    if ruleset_id:
        templates = db.stat_templates.get_by_ruleset(ruleset_id)
        found = next((t for t in templates if t["name"].lower() == stat_template.lower()), None)
        if found:
            template_id = found["id"]
    
    # B. Fallback to Session Default (stat_template_id in manifest)
    if not template_id:
        template_id = manifest.get("stat_template_id")

    # 3. Initialize Entity
    # We create a skeleton matching the Universal Renderer expectations
    npc_data = {
        "name": name_display,
        "description": visual_description,
        "template_id": template_id,
        "location_key": location_key,
        "disposition": initial_disposition,
        "scene_state": {"zone_id": None, "is_hidden": False},
        
        # Default Categories (Empty containers)
        "attributes": {},
        "resources": {"hp": {"current": 10, "max": 10}}, # Basic fallback
        "inventory": {},
        "skills": {},
        "features": {}
    }

    set_entity(session_id, db, "character", key, npc_data)

    # 4. Add to Scene
    scene = get_entity(session_id, db, "scene", "active_scene")
    if not scene:
        scene = {"members": [], "location_key": location_key}
    
    member_id = f"character:{key}"
    if member_id not in scene.get("members", []):
        scene.setdefault("members", []).append(member_id)
        set_entity(session_id, db, "scene", "active_scene", scene)
    
    # 5. Profile
    npc_profile = {
        "personality_traits": context.get("personality_traits", []),
        "motivations": ["Survive"],
        "directive": "idle",
        "relationships": {},
        "last_updated_time": context.get("current_game_time", "Day 1")
    }
    set_entity(session_id, db, "npc_profile", key, npc_profile)

    return {"success": True, "key": key}
