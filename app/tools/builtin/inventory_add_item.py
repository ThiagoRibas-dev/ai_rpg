from typing import Optional, Dict, Any
from app.services.state_service import get_entity, set_entity
from app.models.sheet_schema import CharacterSheetSpec

def handler(
    owner_key: str,
    item_name: str,
    quantity: int = 1,
    target_slot: Optional[str] = None,
    description: Optional[str] = None,
    properties: Optional[Dict[str, Any]] = None,
    **context,
) -> dict:
    session_id = context["session_id"]
    db = context["db_manager"]

    entity = get_entity(session_id, db, "character", owner_key)
    if not entity:
        raise ValueError("Owner not found")

    tid = entity.get("template_id")
    template = db.stat_templates.get_by_id(tid) if tid else None

    # Resolve Collection ID
    col_id = target_slot
    
    # Try to deduce from Template if not specified
    if not col_id and template and isinstance(template, CharacterSheetSpec):
        # Look in the 'inventory' category for a repeater
        if template.inventory and template.inventory.fields:
            for key, field in template.inventory.fields.items():
                if getattr(field, "container_type", "") == "list":
                    col_id = key
                    break
    
    # Fallback
    if not col_id:
        col_id = "inventory"

    # Update Data
    cols = entity.setdefault("inventory", {}) # Note: New schema puts lists in categories, but entity might store them flat or nested.
    # For compatibility with the new renderer, we expect: entity['inventory']['backpack'] = []
    # But let's check if 'inventory' is a dict or list in the entity currently.
    
    # Case A: Entity uses new schema nesting (inventory -> backpack -> list)
    if isinstance(cols, dict):
        if col_id not in cols:
            cols[col_id] = []
        items = cols[col_id]
    # Case B: Entity uses old flat collections (inventory -> list) - Legacy Fallback
    elif isinstance(cols, list):
        items = cols
    else:
        # Should not happen, but reset if weird
        cols = {col_id: []}
        entity["inventory"] = cols
        items = cols[col_id]

    # Check existing item stack
    found = False
    for item in items:
        if item.get("name") == item_name:
            item["qty"] = item.get("qty", 1) + quantity
            if description:
                item["description"] = description
            if properties:
                item.update(properties)
            found = True
            break

    if not found:
        new_item = {
            "name": item_name,
            "qty": quantity,
            "description": description or "",
        }
        if properties:
            new_item.update(properties)

        items.append(new_item)

    # Save back
    set_entity(session_id, db, "character", owner_key, entity)
    return {"success": True, "item": item_name, "collection": col_id}
