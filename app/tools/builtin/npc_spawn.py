from typing import Any, Optional
from app.services.state_service import get_entity, set_entity
from app.prefabs.manifest import SystemManifest, EngineConfig, FieldDef
from app.prefabs.validation import validate_entity

# --- MINIMAL NPC FALLBACK ---
MINIMAL_NPC_MANIFEST = SystemManifest(
    id="minimal_npc",
    name="Simple NPC",
    engine=EngineConfig(dice="1d20", mechanic="Roll vs DC", success=">= DC", crit="Nat 20"),
    fields=[
        FieldDef(path="resources.hp", label="Hit Points", prefab="RES_POOL", category="resources", config={"default_max": 10}),
        FieldDef(path="combat.ac", label="Armor Class", prefab="VAL_INT", category="combat", config={"default": 10}),
        FieldDef(path="combat.initiative", label="Initiative", prefab="VAL_INT", category="combat", config={"default": 0}),
        FieldDef(path="inventory.loot", label="Loot", prefab="CONT_LIST", category="inventory"),
        FieldDef(path="features.attacks", label="Attacks", prefab="CONT_LIST", category="features")
    ]
)

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

    # 2. Resolve Template Strategy
    manifest_to_use = None
    
    # Strategy A: Look for a SystemManifest matching the requested template name
    # e.g. stat_template="dnd_5e" or "Cyberpunk Guard"
    all_manifests = db.manifests.get_all()
    
    # 1. Try exact ID match
    found_meta = next((m for m in all_manifests if m["system_id"] == stat_template), None)
    
    # 2. Try Name match (case-insensitive)
    if not found_meta:
        found_meta = next((m for m in all_manifests if m["name"].lower() == stat_template.lower()), None)
    
    if found_meta:
        # Load the full manifest
        manifest_to_use = db.manifests.get_by_id(found_meta["id"])

    # Strategy B: Fallback to Minimal
    if not manifest_to_use:
        manifest_to_use = MINIMAL_NPC_MANIFEST

    # 3. Initialize Entity Structure
    npc_data = {
        "name": name_display,
        "description": visual_description,
        "location_key": location_key,
        "disposition": initial_disposition,
        "scene_state": {"zone_id": None, "is_hidden": False},
        
        # We store the ID if it's a real DB manifest, else None for Minimal
        "template_id": found_meta["id"] if found_meta else None,
        
        # Initialize empty containers for all categories in the manifest
        "attributes": {},
        "resources": {},
        "skills": {},
        "inventory": {},
        "features": {},
        "combat": {},
        "status": {},
        "progression": {},
        "meta": {}
    }

    # 4. Hydrate & Validate (Calculates defaults, max HP, etc.)
    # This ensures the NPC has valid starting stats based on the chosen manifest
    npc_data, _ = validate_entity(npc_data, manifest_to_use)

    set_entity(session_id, db, "character", key, npc_data)

    # 5. Add to Scene
    scene = get_entity(session_id, db, "scene", "active_scene")
    if not scene:
        scene = {"members": [], "location_key": location_key}
    
    member_id = f"character:{key}"
    if member_id not in scene.get("members", []):
        scene.setdefault("members", []).append(member_id)
        set_entity(session_id, db, "scene", "active_scene", scene)
    
    # 6. Profile
    npc_profile = {
        "personality_traits": context.get("personality_traits", []),
        "motivations": ["Survive"],
        "directive": "idle",
        "relationships": {},
        "last_updated_time": context.get("current_game_time", "Day 1")
    }
    set_entity(session_id, db, "npc_profile", key, npc_profile)

    return {
        "success": True, 
        "key": key, 
        "template_used": manifest_to_use.name
    }
