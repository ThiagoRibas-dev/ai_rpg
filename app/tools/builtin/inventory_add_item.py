from typing import Optional, Dict, Any
from app.tools.builtin._state_storage import get_entity, set_entity


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
    if not col_id and template:
        # Find first collection in 'equipment' panel
        for c_id, c_def in template.collections.items():
            if c_def.panel == "equipment":
                col_id = c_id
                break

    if not col_id:
        col_id = "inventory"  # Fallback

    # Update Data
    cols = entity.setdefault("collections", {})
    items = cols.setdefault(col_id, [])

    # Check existing
    found = False
    for item in items:
        if item.get("name") == item_name:
            item["qty"] = item.get("qty", 1) + quantity
            # Update metadata if provided (merge strategy)
            if description:
                item["description"] = description
            if properties:
                item.update(properties)  # Merge new props into existing item
            found = True
            break

    if not found:
        # Create new item structure
        new_item = {
            "name": item_name,
            "qty": quantity,
            "description": description or "",
        }
        if properties:
            new_item.update(properties)  # Flatten properties into the item dict

        items.append(new_item)

    set_entity(session_id, db, "character", owner_key, entity)
    return {"success": True, "item": item_name, "collection": col_id}
