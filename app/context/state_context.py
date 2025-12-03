import logging
from typing import List
from app.tools.registry import ToolRegistry
from app.tools.schemas import StateQuery
from app.services.state_service import get_entity
from app.models.sheet_schema import CharacterSheetSpec


class StateContextBuilder:
    """
    Builds the CURRENT STATE section by querying game state.
    Refactored to support Dynamic CharacterSheetSpec.
    """

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
            # 1. Load Player Entity & Template
            player = get_entity(session_id, self.db, "character", "player")
            if not player:
                return "No character data found."

            tid = player.get("template_id")
            template = self.db.stat_templates.get_by_id(tid) if tid else None

            # If no template, we can't render semantically, just dump raw?
            # Better to try to render what we can find.

            name = player.get("name", "Player")
            lines.append(f"**Player Character**: {name}")

            # 2. Render Categories (Dynamic)
            # We want to present this to the LLM in a clean, dense format.

            # Categories to include in context (in order of importance)
            cats = [
                "attributes",
                "resources",
                "skills",
                "features",
                "inventory",
                "connections",
                "narrative",
            ]

            # Helper to get field definition
            def get_field_def(cat, key):
                if template and isinstance(template, CharacterSheetSpec):
                    cat_obj = getattr(template, cat, None)
                    if cat_obj and cat_obj.fields:
                        return cat_obj.fields.get(key)
                return None

            for cat in cats:
                data = player.get(cat, {})
                if not data:
                    continue

                cat_lines = []

                for key, val in data.items():
                    # Get definition for label
                    field_def = get_field_def(cat, key)
                    label = (
                        field_def.display.label
                        if field_def
                        else key.replace("_", " ").title()
                    )

                    # Formatting based on value type
                    display_val = str(val)

                    # Case: Pool (Current/Max)
                    if isinstance(val, dict) and "current" in val:
                        curr = val.get("current", 0)
                        mx = val.get("max", "?")
                        display_val = f"{curr}/{mx}"

                    # Case: List (Inventory/Skills)
                    elif isinstance(val, list):
                        if not val:
                            continue
                        items = []
                        for item in val:
                            if isinstance(item, dict):
                                i_name = item.get("name", "Item")
                                i_qty = item.get("qty", 1)
                                qty_str = f" x{i_qty}" if i_qty > 1 else ""
                                items.append(f"{i_name}{qty_str}")
                            else:
                                items.append(str(item))
                        display_val = ", ".join(items)

                    cat_lines.append(f"{label}: {display_val}")

                if cat_lines:
                    lines.append(f"**{cat.capitalize()}**: " + ", ".join(cat_lines))

            # 3. Active Quests (Legacy/Side-channel)
            # Quests might still use the old 'quest' entity type, which is fine.
            quest_result = self.tools.execute(
                StateQuery(entity_type="quest", key="*", json_path="."),
                context={"session_id": session_id, "db_manager": self.db},
            )
            quests = quest_result.get("value", {}) or {}

            if quests and isinstance(quests, dict):
                active_q = []
                for q in quests.values():
                    if q.get("status") == "active":
                        active_q.append(
                            f"{q.get('title')} ({q.get('description', '')[:50]}...)"
                        )

                if active_q:
                    lines.append("")
                    lines.append("**Active Quests**:")
                    for q in active_q:
                        lines.append(f"- {q}")

        except Exception as e:
            if self.logger:
                self.logger.warning(f"State build failed: {e}", exc_info=True)

        return "\n".join(lines)
