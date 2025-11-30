import logging
from typing import List
from app.tools.registry import ToolRegistry
from app.tools.schemas import StateQuery
from app.tools.builtin._state_storage import get_entity


class StateContextBuilder:
    """Builds the CURRENT STATE section by querying game state via tools."""

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
                if not items:
                    continue
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
                    lines.append(f"...and {len(items) - 8} more.")
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

        return "\n".join(lines)
