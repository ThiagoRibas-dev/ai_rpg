from typing import Any
from app.tools.builtin._state_storage import get_entity
from app.tools.builtin.state_apply_patch import handler as apply_patch


def handler(
    owner_key: str,
    item_name: str,
    quantity: int = 1,
    **context: Any,
) -> dict:
    """
    Handler for inventory.remove_item. Decrements quantity or removes the item.
    """
    inventory = get_entity(context["session_id"], context["db_manager"], "inventory", owner_key)

    if not inventory or not inventory.get("items"):
        return {"success": False, "error": "Inventory not found or is empty."}

    items = inventory.get("items", [])
    
    for i, item in enumerate(items):
        if item.get("name", "").lower() == item_name.lower():
            current_quantity = item.get("quantity", 1)
            
            if current_quantity > quantity:
                # Decrement quantity
                new_quantity = current_quantity - quantity
                patch = [{"op": "replace", "path": f"/items/{i}/quantity", "value": new_quantity}]
                apply_patch("inventory", owner_key, patch, **context)
                return {"success": True, "action": "decremented", "item_name": item_name, "new_quantity": new_quantity}
            else:
                # Remove the item entirely
                patch = [{"op": "remove", "path": f"/items/{i}"}]
                
                # Also update slots_used
                if "slots_used" in inventory:
                    patch.append({"op": "replace", "path": "/slots_used", "value": inventory.get("slots_used", 1) - 1})

                apply_patch("inventory", owner_key, patch, **context)
                return {"success": True, "action": "removed", "item_name": item_name}

    return {"success": False, "error": f"Item '{item_name}' not found in inventory."}
