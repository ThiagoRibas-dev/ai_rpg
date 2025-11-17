import time
from typing import Optional, Dict, Any
from app.tools.builtin._state_storage import get_entity, set_entity


def handler(
    owner_key: str,
    item_name: str,
    quantity: int = 1,
    description: Optional[str] = None,
    properties: Optional[Dict[str, Any]] = None,
    **context: Any,
) -> dict:
    """
    Handler for inventory.add_item. It intelligently handles adding a new item
    or incrementing the quantity of an existing one.
    """
    session_id = context["session_id"]
    db = context["db_manager"]

    inventory = get_entity(context["session_id"], context["db_manager"], "inventory", owner_key)

    if not inventory:
        # If no inventory exists, create a basic one.
        inventory = {"owner": owner_key, "items": [], "currency": {}, "slots_used": 0, "slots_max": 10}

    items = inventory.get("items", [])
    
    item_found_and_incremented = False
    # Check if item already exists
    for i, item in enumerate(items):
        if item.get("name", "").lower() == item_name.lower():
            # Item found, increment quantity
            inventory["items"][i]["quantity"] = item.get("quantity", 1) + quantity
            item_found_and_incremented = True
            break
    
    if not item_found_and_incremented:
        # Item not found, create and add it
        new_item = {
            "id": f"item_{int(time.time())}",
            "name": item_name,
            "quantity": quantity,
            "description": description or "",
            "equipped": False,
            "properties": properties or {},
        }
        inventory.setdefault("items", []).append(new_item)
        
        # Also update slots_used if the inventory has that property
        if "slots_used" in inventory:
            inventory["slots_used"] = inventory.get("slots_used", 0) + 1

    set_entity(session_id, db, "inventory", owner_key, inventory)

    return {"success": True, "action": "incremented" if item_found_and_incremented else "added", "item_name": item_name}
