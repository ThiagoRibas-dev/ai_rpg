import logging
from typing import List, Optional, Any
from app.tools.registry import ToolRegistry
from app.tools.schemas import StateQuery
from app.services.state_service import get_entity
from app.prefabs.manifest import SystemManifest
from app.prefabs.validation import get_path


class StateContextBuilder:
    """
    Builds the CURRENT STATE section.
    Uses SystemManifest to render fields intelligently (Prefabs).
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

    def build(
        self, session_id: int | None, manifest: Optional[SystemManifest] = None
    ) -> str:
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

            # 2. Render Categories via Manifest
            if manifest:
                for category in manifest.get_categories():
                    fields = manifest.get_fields_by_category(category)
                    if not fields:
                        continue

                    cat_lines = []
                    for field in fields:
                        # Get raw value from entity
                        val = get_path(player, field.path)
                        # Render based on Prefab Type
                        rendered = self._render_field(val, field.prefab)

                        # Only show if not None/Empty, unless it's a vital stat
                        if rendered:
                            cat_lines.append(f"{field.label}: {rendered}")

                    if cat_lines:
                        lines.append(f"**{category.title()}**: " + ", ".join(cat_lines))
            else:
                # Legacy Fallback
                lines.append(self._legacy_render(player))

            # 3. Active Quests (Standard Tool)
            quest_result = self.tools.execute(
                StateQuery(entity_type="quest", key="*", json_path="."),
                context={"session_id": session_id, "db_manager": self.db},
            )
            quests = quest_result.get("value", {}) or {}
            if quests and isinstance(quests, dict):
                active_q = [
                    f"{q.get('title')}"
                    for q in quests.values()
                    if q.get("status") == "active"
                ]
                if active_q:
                    lines.append("\n**Active Quests**: " + ", ".join(active_q))

            # 4. Scene Roster
            scene = self.db.game_state.get_entity(session_id, "scene", "active_scene")
            if scene and "members" in scene:
                roster = []
                for member in scene["members"]:
                    if "player" in member:
                        continue
                    if ":" in member:
                        etype, ekey = member.split(":", 1)
                        ent = self.db.game_state.get_entity(session_id, etype, ekey)
                        if ent:
                            roster.append(
                                f"{ent.get('name', 'Unknown')} (ID: `{ekey}`)"
                            )
                if roster:
                    lines.append("\n**SCENE ROSTER**:\n- " + "\n- ".join(roster))

        except Exception as e:
            if self.logger:
                self.logger.warning(f"State build failed: {e}", exc_info=True)

        return "\n".join(lines)

    def _render_field(self, value: Any, prefab: str) -> str:
        """Render value based on prefab type for the LLM Context."""
        if value is None:
            return ""

        if prefab == "RES_POOL":
            # Render as Current/Max
            if isinstance(value, dict):
                curr = value.get("current", 0)
                mx = value.get("max", 0)
                return f"{curr}/{mx}"
            return str(value)

        elif prefab == "RES_TRACK":
            # Render as visual dots: [x][x][ ]
            if isinstance(value, list):
                return "".join(["[x]" if x else "[ ]" for x in value])
            return str(value)

        elif prefab == "VAL_COMPOUND":
            # Render as Score (+Mod)
            if isinstance(value, dict):
                score = value.get("score", 0)
                mod = value.get("mod", 0)
                sign = "+" if mod >= 0 else ""
                return f"{score} ({sign}{mod})"
            return str(value)

        elif prefab == "VAL_LADDER":
            # Render as +1 (Average)
            if isinstance(value, dict):
                val = value.get("value", 0)
                lbl = value.get("label", "")
                sign = "+" if val >= 0 else ""
                return f"{sign}{val} ({lbl})"
            return str(value)

        elif prefab == "CONT_LIST":
            # Concise list: [Sword, Shield]
            if isinstance(value, list):
                items = []
                for item in value:
                    if isinstance(item, dict):
                        name = item.get("name", "Item")
                        qty = item.get("qty", 1)
                        if qty > 1:
                            items.append(f"{name} x{qty}")
                        else:
                            items.append(name)
                    else:
                        items.append(str(item))
                if not items:
                    return "Empty"
                return "[" + ", ".join(items) + "]"
            return "[]"

        elif prefab == "CONT_TAGS":
            if isinstance(value, list):
                return "[" + ", ".join(str(v) for v in value) + "]"
            return "[]"

        return str(value)

    def _legacy_render(self, player) -> str:
        """Old renderer for compatibility."""
        return "Legacy Character Data (No Manifest Loaded)"
