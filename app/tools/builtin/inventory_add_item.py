import time
from typing import Optional, Dict, Any
from app.tools.builtin._state_storage import get_entity


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
    inventory = get_entity(context["session_id"], context["db_manager"], "inventory", owner_key)

    if not inventory:
        # If no inventory exists, create a basic one.
        inventory = {"items": [], "currency": {}, "slots_used": 0, "slots_max": 10}

    items = inventory.get("items", [])
    
    # Check if item already exists
    for i, item in enumerate(items):
        if item.get("name", "").lower() == item_name.lower():
            # Item found, increment quantity
            new_quantity = item.get("quantity", 1) + quantity
            patch = [{"op": "replace", "path": f"/items/{i}/quantity", "value": new_quantity}]
            return {"success": True, "action": "incremented", "item_name": item_name, "new_quantity": new_quantity}

    # Item not found, create and add it
    new_item = {
        "id": f"item_{int(time.time())}",
        "name": item_name,
        "quantity": quantity,
        "description": description or "",
        "equipped": False,
        "properties": properties or {},
    }

    patch = [{"op": "add", "path": "/items/-", "value": new_item}]
    
    # Also update slots_used if the inventory has that property
    if "slots_used" in inventory:
        patch.append({"op": "replace", "path": "/slots_used", "value": inventory.get("slots_used", 0) + 1})

    return {"success": True, "action": "added", "item": new_item}
