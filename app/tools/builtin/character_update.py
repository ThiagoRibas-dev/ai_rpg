import logging
from typing import Any, Dict, List
from app.tools.builtin.entity_update import handler as entity_update_handler

logger = logging.getLogger(__name__)

def handler(character_key: str, updates: List[Dict[str, Any]], **context) -> dict:
    """
    Legacy wrapper that maps list-based updates to the dictionary format 
    expected by entity_update.
    """
    # Convert [{"key": "str", "value": 10}] -> {"str": 10}
    update_dict = {}
    for item in updates:
        update_dict[item["key"]] = item["value"]

    return entity_update_handler(
        target_key=character_key,
        updates=update_dict,
        **context
    )
