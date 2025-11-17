from typing import Any
from app.tools.builtin._state_storage import get_entity, set_entity


def handler(
    owner_key: str,
    item_name: str,
    quantity: int = 1,
    **context: Any,
) -> dict:
    """
    Handler for inventory.remove_item. Decrements quantity or removes the item.
    """
    session_id = context["session_id"]
    db = context["db_manager"]
    inventory = get_entity(session_id, db, "inventory", owner_key)

    if not inventory or not inventory.get("items"):
        return {"success": False, "error": "Inventory not found or is empty."}

    items = inventory.get("items", [])
    
    item_index_to_remove = -1
    for i, item in enumerate(items):
        if item.get("name", "").lower() == item_name.lower():
            current_quantity = item.get("quantity", 1)
            
            if current_quantity > quantity:
                # Decrement quantity
                inventory["items"][i]["quantity"] = current_quantity - quantity
                set_entity(session_id, db, "inventory", owner_key, inventory)
                return {"success": True, "action": "decremented", "item_name": item_name, "new_quantity": inventory["items"][i]["quantity"]}
            else:
                # Mark the item for removal after the loop
                item_index_to_remove = i
                break
    
    if item_index_to_remove != -1:
        # Remove the item outside the loop to avoid modifying it while iterating
        inventory["items"].pop(item_index_to_remove)
        
        # Also update slots_used
        if "slots_used" in inventory:
            inventory["slots_used"] = inventory.get("slots", 1) - 1
        
        set_entity(session_id, db, "inventory", owner_key, inventory)
        return {"success": True, "action": "removed", "item_name": item_name}

    return {"success": False, "error": f"Item '{item_name}' not found in inventory."}
