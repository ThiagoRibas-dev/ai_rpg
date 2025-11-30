import os

FILES = {}

# ==============================================================================
# 1. STATE CONTEXT: READ FUNDAMENTALS & DERIVED
# ==============================================================================
FILES["app/context/state_context.py"] = """
import logging
from typing import List
from app.tools.registry import ToolRegistry
from app.tools.schemas import StateQuery
from app.tools.builtin._state_storage import get_entity

class StateContextBuilder:
    \"\"\"Builds the CURRENT STATE section by querying game state via tools.\"\"\"

    def __init__(
        self,
        tool_registry: ToolRegistry,
        db_manager,
        logger: logging.Logger | None = None,
    ):
        self.tools = tool_registry
        self.db = db_manager
        self.logger = logger or logging.getLogger(__name__)

    def build(self, session_id: int | None) -> str:
        if not session_id:
            return ""

        lines: List[str] = []
        try:
            # 1. Load Player Entity
            player = get_entity(session_id, self.db, "character", "player")
            if not player:
                return "No character data found."
            
            name = player.get("name", "Player")
            lines.append(f"**Player Character**: {name}")

            # 2. Fundamentals (Inputs)
            fundamentals = player.get("fundamentals", {})
            if fundamentals:
                lines.append("**Attributes & Inputs**:")
                # Simple formatting
                lines.append(", ".join([f"{k}: {v}" for k, v in fundamentals.items()]))
                lines.append("")

            # 3. Derived (Outputs)
            derived = player.get("derived", {})
            if derived:
                lines.append("**Combat & Stats**:")
                lines.append(", ".join([f"{k}: {v}" for k, v in derived.items()]))
                lines.append("")

            # 4. Gauges (Resources)
            gauges = player.get("gauges", {})
            if gauges:
                lines.append("**Vitals**:")
                vital_strs = []
                for k, v in gauges.items():
                    if isinstance(v, dict):
                        curr = v.get("current", 0)
                        mx = v.get("max", "?")
                        vital_strs.append(f"{k}: {curr}/{mx}")
                    else:
                        vital_strs.append(f"{k}: {v}")
                lines.append(", ".join(vital_strs))
                lines.append("")

            # 5. Collections (Inventory, Skills, etc)
            cols = player.get("collections", {})
            for col_id, items in cols.items():
                if not items: continue
                # Only show first few items to save tokens
                lines.append(f"**{col_id.replace('_', ' ').title()}** ({len(items)}):")
                item_strs = []
                for item in items[:8]:
                    name = item.get("name", "???")
                    qty = item.get("qty", 1)
                    s = f"{name}" + (f" (x{qty})" if qty > 1 else "")
                    item_strs.append(s)
                lines.append(", ".join(item_strs))
                if len(items) > 8:
                    lines.append(f"...and {len(items)-8} more.")
                lines.append("")

            # 6. Active Quests (via Tool)
            ctx = {"session_id": session_id, "db_manager": self.db}
            quest_query = StateQuery(entity_type="quests", key="*", json_path=".")
            quest_result = self.tools.execute(quest_query, context=ctx)
            quests = quest_result.get("value", {}) or {}
            
            if quests and isinstance(quests, dict):
                lines.append("**Active Quests**:")
                for qid, q in list(quests.items())[:3]:
                    title = q.get("title", "Unknown")
                    status = q.get("status", "active")
                    lines.append(f"- {title} ({status})")

        except Exception as e:
            if self.logger:
                self.logger.warning(f"State build failed: {e}")

        return "\\n".join(lines)
"""

# ==============================================================================
# 2. ENTITY UPDATE: WRITE TO FUNDAMENTALS & DERIVED
# ==============================================================================
FILES["app/tools/builtin/entity_update.py"] = """
from typing import Any, Dict, Optional
from app.tools.builtin._state_storage import get_entity, set_entity

def handler(
    target_key: str,
    updates: Optional[Dict[str, Any]] = None,
    adjustments: Optional[Dict[str, int]] = None,
    inventory: Optional[Dict[str, Any]] = None,
    **context: Any
) -> dict:
    session_id = context["session_id"]
    db = context["db_manager"]

    # Handle "player" alias
    etype = "character"
    if ":" in target_key:
        etype, target_key = target_key.split(":", 1)

    entity = get_entity(session_id, db, etype, target_key)
    if not entity:
        return {"error": "Entity not found"}

    changes_log = []

    # 1. Adjustments (Relative Math)
    if adjustments:
        for k, delta in adjustments.items():
            # Check Fundamentals
            if k in entity.get("fundamentals", {}):
                old = entity["fundamentals"][k]
                entity["fundamentals"][k] += delta
                changes_log.append(f"{k}: {old} -> {entity['fundamentals'][k]}")
            
            # Check Derived (Manual Override)
            elif k in entity.get("derived", {}):
                old = entity["derived"][k]
                entity["derived"][k] += delta
                changes_log.append(f"{k}: {old} -> {entity['derived'][k]}")

            # Check Gauges
            elif k in entity.get("gauges", {}):
                g = entity["gauges"][k]
                old = g["current"]
                # Clamp between 0 and Max
                mx = g.get("max", 9999)
                g["current"] = max(0, min(g["current"] + delta, mx))
                changes_log.append(f"{k}: {old} -> {g['current']}")

    # 2. Updates (Absolute Set)
    if updates:
        for k, v in updates.items():
            if k in entity.get("fundamentals", {}):
                entity["fundamentals"][k] = v
            elif k in entity.get("derived", {}):
                entity["derived"][k] = v
            elif k in entity.get("gauges", {}):
                # Handle direct int set vs dict set
                if isinstance(v, (int, float)):
                    entity["gauges"][k]["current"] = v
                elif isinstance(v, dict):
                    entity["gauges"][k].update(v)
            else:
                # Fallback to root (e.g. name, location_key)
                entity[k] = v
            changes_log.append(f"Set {k} = {v}")

    # 3. Inventory (Add only for now)
    if inventory and "add" in inventory:
        item = inventory["add"]
        # Default collection: find first available or make 'inventory'
        col_map = entity.setdefault("collections", {})
        col_key = "inventory"
        if "inventory" not in col_map and col_map:
            col_key = next(iter(col_map))
        
        target_list = col_map.setdefault(col_key, [])
        target_list.append(item)
        changes_log.append(f"Added {item.get('name')} to {col_key}")

    set_entity(session_id, db, etype, target_key, entity)
    return {"success": True, "changes": changes_log}
"""


def apply_update():
    print("ðŸ”§ Patching Context & Entity Update to use 'fundamentals'...")
    for filepath, content in FILES.items():
        filepath = filepath.replace("/", os.sep)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        print(f"ðŸ“  Updating {filepath}...")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    print("âœ… Done.")


if __name__ == "__main__":
    apply_update()
