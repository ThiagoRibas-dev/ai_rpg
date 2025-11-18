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
    """Handler for inventory.add_item. Adds item to an appropriate Slot in the character's StatBlock."""
    session_id = context["session_id"]
    db = context["db_manager"]

    # 1. Load Owner (Character)
    owner = get_entity(session_id, db, "character", owner_key)
    if not owner:
        raise ValueError(f"Owner '{owner_key}' not found.")

    # 2. Determine Slot
    # We need to find a slot definition that accepts items.
    template_id = owner.get("template_id")
    stat_template = None
    if template_id:
        stat_template = db.stat_templates.get_by_id(template_id)
    
    target_slot_name = "Inventory" # Default fallback
    
    if stat_template:
        # Find the first slot that accepts "item" or has "inventory" in name
        for slot_def in stat_template.slots:
            if "item" in slot_def.accepts_tags or "Inventory" in slot_def.name:
                target_slot_name = slot_def.name
                break
    
    # 3. Access Slot Data
    slots_data = owner.setdefault("slots", {})
    target_slot_items = slots_data.setdefault(target_slot_name, [])
    
    # 4. Logic: Increment or Add
    action = "added"
    found = False
    
    for item in target_slot_items:
        if item.get("name") == item_name:
            item["quantity"] = item.get("quantity", 1) + quantity
            found = True
            action = "incremented"
            break
    
    if not found:
        new_item = {
            "id": f"item_{int(time.time())}",
            "name": item_name,
            "quantity": quantity,
            "description": description or "",
            "properties": properties or {}
        }
        target_slot_items.append(new_item)
    
    # 5. Capacity Check (Simple count check for now)
    # Ideally we use StateValidator._validate_slot, but for now simple length check if fixed capacity exists
    if stat_template:
        slot_def = next((s for s in stat_template.slots if s.name == target_slot_name), None)
        if slot_def and slot_def.fixed_capacity:
            # Simple logic: count distinct items or sum quantities? 
            # Let's assume sum quantities for simplicity in this patch
            total_count = sum(i.get("quantity", 1) for i in target_slot_items)
            if total_count > slot_def.fixed_capacity:
                 if slot_def.overflow_behavior == "prevent":
                     raise ValueError(f"Slot '{target_slot_name}' is full (Capacity: {slot_def.fixed_capacity}).")
                 # Else warn?
    
    # 6. Save
    set_entity(session_id, db, "character", owner_key, owner)

    return {
        "success": True, 
        "action": action, 
        "item_name": item_name,
        "slot": target_slot_name
    }
