import logging
from typing import List
from app.tools.registry import ToolRegistry
from app.tools.schemas import StateQuery


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
            if self.logger:
                self.logger.debug("StateContextBuilder: no session_id, skipping.")
            return ""

        lines: List[str] = []
        ctx = {"session_id": session_id, "db_manager": self.db}

        try:
            # Character
            char_query = StateQuery(
                entity_type="character", key="player", json_path="."
            )
            char_result = self.tools.execute(char_query, context=ctx)

            char = char_result.get("value", {}) or {}
            if char:
                name = char.get("name", "Player")
                race = char.get("race", "")
                char_class = char.get("class", "")
                level = char.get("level", 1)
                lines.append(
                    f"**Character**: {name} ({race} {char_class}, Level {level})"
                )
                attrs = char.get("attributes", {})
                if attrs:
                    hp = f"{attrs.get('hp_current', '?')}/{attrs.get('hp_max', '?')}"
                    lines.append(f"- HP: {hp}")
                conditions = char.get("conditions", [])
                if conditions:
                    lines.append(f"- Conditions: {', '.join(conditions)}")
                location = char.get("location")
                if location:
                    lines.append(f"- Location: {location}")
                lines.append("")

            # Inventory
            inv_query = StateQuery(entity_type="inventory", key="player", json_path=".")
            inv_result = self.tools.execute(inv_query, context=ctx)

            inv = inv_result.get("value", {}) or {}
            if inv:
                slots = f"{inv.get('slots_used', 0)}/{inv.get('slots_max', 10)}"
                lines.append(f"**Inventory** ({slots} slots):")
                items = inv.get("items", [])
                if items:
                    for item in items[:5]:
                        name = item.get("name", "Unknown")
                        qty = item.get("quantity", 1)
                        equipped = " (equipped)" if item.get("equipped") else ""
                        qty_str = f" x{qty}" if qty and qty > 1 else ""
                        lines.append(f"- {name}{qty_str}{equipped}")
                currency = inv.get("currency", {})
                if currency:
                    curr_str = ", ".join([f"{v} {k}" for k, v in currency.items()])
                    lines.append(f"- Currency: {curr_str}")
                lines.append("")

            # Quests
            quest_query = StateQuery(entity_type="quests", key="*", json_path=".")
            quest_result = self.tools.execute(quest_query, context=ctx)

            quests = quest_result.get("value", {}) or {}
            if quests and isinstance(quests, dict):
                lines.append("**Active Quests**:")
                for quest_id, quest in list(quests.items())[:3]:
                    title = quest.get("title", "Unknown")
                    quest_type = quest.get("type", "side")
                    progress = quest.get("progress", "")
                    type_label = "[Main]" if quest_type == "main" else "[Side]"
                    lines.append(f"- {type_label} {title} ({progress})")
                lines.append("")

        except Exception as e:
            if self.logger:
                self.logger.debug(f"StateContextBuilder: failed to build state: {e}")
            # fail silently into empty

        return "\n".join(lines) if lines else ""
