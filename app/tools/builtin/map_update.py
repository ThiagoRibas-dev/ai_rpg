from typing import Literal, List, Dict
from app.tools.builtin._state_storage import get_entity, set_entity

def handler(
    operation: Literal["init", "move", "terrain"],
    width: int = 5,
    height: int = 5,
    entities: Dict[str, str] = None, # {"player": "A1"}
    terrain: List[str] = None, # ["C3", "C4"]
    **context
) -> dict:
    """
    Manage the tactical map.
    operations:
    - init: Create a new grid (width/height) and clear positions.
    - move: Update entity positions (e.g., entities={"player": "B2"}).
    - terrain: Set wall/obstacle positions.
    """
    session_id = context["session_id"]
    db = context["db_manager"]
    
    scene = get_entity(session_id, db, "scene", "active_scene")
    if not scene:
        return {"error": "No active scene"}
    
    tmap = scene.get("tactical_map", {"width": 5, "height": 5, "positions": {}, "terrain": {}})
    
    if operation == "init":
        tmap = {
            "width": width, 
            "height": height, 
            "positions": {}, 
            "terrain": {}
        }
        # Auto-place entities if provided
        if entities:
            for key, coord in entities.items():
                # keys might be short names, resolve to full keys if needed
                # For now, assume simple mapping or UI handles display
                tmap["positions"][key] = coord

    elif operation == "move":
        if entities:
            for key, coord in entities.items():
                # Simple algebraic validation (optional but good)
                tmap["positions"][key] = coord

    elif operation == "terrain":
        if terrain:
            for coord in terrain:
                tmap["terrain"][coord] = "wall"

    scene["tactical_map"] = tmap
    set_entity(session_id, db, "scene", "active_scene", scene)
    
    # Signal UI to refresh map
    if context.get("ui_queue"):
        context["ui_queue"].put({
            "type": "map_update", 
            "data": {
                "width": tmap["width"],
                "height": tmap["height"],
                "entities": {k: v for k, v in tmap["positions"].items()}, # Flip for UI? UI expects Coord -> Key?
                # UI expects {"A1": "player"}, data is {"player": "A1"}
                # Let's fix format for UI in the view handler
                "terrain": tmap["terrain"]
            }
        })

    return {"success": True, "operation": operation, "map_state": str(tmap)}
