import time
import logging
from typing import Optional, Dict, Any
from app.tools.builtin._state_storage import get_entity, set_entity

logger = logging.getLogger(__name__)

def handler(
    owner_key: str,
    item_name: str,
    quantity: int = 1,
    description: Optional[str] = None,
    properties: Optional[Dict[str, Any]] = None,
    target_slot: Optional[str] = None,
    **context: Any,
) -> dict:
    """
    Handler for inventory.add_item. 
    Adds item to an appropriate Slot in the character's StatBlock.
    If target_slot is provided, it forces creation/usage of that slot (Narrative Game style).
    """
    session_id = context["session_id"]
    db = context["db_manager"]

    # 1. Load Owner (Character)
    owner = get_entity(session_id, db, "character", owner_key)
    if not owner:
        raise ValueError(f"Owner '{owner_key}' not found.")

    # 2. Determine Slot
    target_slot_name = "Inventory" # Default fallback

    # TWEAK: Check for manual override first
    if target_slot:
        target_slot_name = target_slot
        logger.info(f"Adding item to requested slot: {target_slot_name}")
    else:
        # Template-based logic
        template_id = owner.get("template_id")
        stat_template = None
        if template_id:
            stat_template = db.stat_templates.get_by_id(template_id)
        
        if stat_template:
            # Find the first slot that accepts "item" or has "inventory" in name
            for slot_def in stat_template.slots:
                if "item" in slot_def.accepts_tags or "Inventory" in slot_def.name:
                    target_slot_name = slot_def.name
                    break
    
    # 3. Access Slot Data
    slots_data = owner.setdefault("slots", {})
    # This line effectively creates dynamic slots if they don't exist
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
    
    # 5. Capacity Check
    # We only check capacity if we found a template definition AND we aren't overriding
    if not target_slot:
        template_id = owner.get("template_id")
        stat_template = db.stat_templates.get_by_id(template_id) if template_id else None
        
        if stat_template:
            slot_def = next((s for s in stat_template.slots if s.name == target_slot_name), None)
            if slot_def and slot_def.fixed_capacity:
                total_count = sum(i.get("quantity", 1) for i in target_slot_items)
                if total_count > slot_def.fixed_capacity:
                     if slot_def.overflow_behavior == "prevent":
                         raise ValueError(f"Slot '{target_slot_name}' is full (Capacity: {slot_def.fixed_capacity}).")
    
    # 6. Save
    set_entity(session_id, db, "character", owner_key, owner)

    return {
        "success": True, 
        "action": action, 
        "item_name": item_name,
        "slot": target_slot_name
    }
