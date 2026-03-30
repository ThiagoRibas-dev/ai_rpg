import logging
from typing import Any
from app.tools.registry import ToolRegistry
from app.tools.schemas import StateQuery
from app.services.state_service import get_entity
from app.prefabs.manifest import SystemManifest
from app.prefabs.validation import get_path
from app.models.vocabulary import PrefabID, FieldKey


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


    def build_character_sheet(self, session_id: int, manifest: SystemManifest) -> str:
        """Renders character categories into clean Markdown tables based on Prefab type."""
        player = get_entity(session_id, self.db, "character", "player")
        if not player:
            return "No character data found."

        name = player.get(FieldKey.NAME, "Player")
        sections = [f"**Player Character**: {name}"]

        for category in manifest.get_categories():
            fields = manifest.get_fields_by_category(category)
            if not fields:
                continue

            prefabs = {f.prefab for f in fields}
            rows = []
            header = None
            sep = None

            if PrefabID.VAL_COMPOUND in prefabs:
                header = "| Attribute | Score | Mod |"
                sep = "| :--- | :--- | :--- |"
                for f in fields:
                    val = get_path(player, f.path)
                    if isinstance(val, dict):
                        score = val.get(FieldKey.SCORE, 0)
                        mod = val.get(FieldKey.MOD, 0)
                        rows.append(f"| {f.label} | {score} | {mod:+} |")
            
            elif PrefabID.RES_POOL in prefabs:
                header = "| Resource | Current | Max |"
                sep = "| :--- | :--- | :--- |"
                for f in fields:
                    val = get_path(player, f.path)
                    if isinstance(val, dict):
                        curr = val.get(FieldKey.CURRENT, 0)
                        mx = val.get(FieldKey.MAX, 0)
                        rows.append(f"| {f.label} | {curr} | {mx} |")

            elif PrefabID.CONT_LIST in prefabs:
                header = "| Item | Qty | Description/Tags |"
                sep = "| :--- | :--- | :--- |"
                for f in fields:
                    val = get_path(player, f.path)
                    if isinstance(val, list):
                        for item in val:
                            if isinstance(item, dict):
                                i_name = item.get(FieldKey.NAME, "Item")
                                i_qty = item.get(FieldKey.QTY, 1)
                                i_desc = item.get("description") or item.get("tags") or ""
                                if isinstance(i_desc, list):
                                    i_desc = ", ".join(str(x) for x in i_desc)
                                rows.append(f"| {i_name} | {i_qty} | {i_desc} |")

            if header and rows:
                sections.append(f"**{category.title()}**\n{header}\n{sep}\n" + "\n".join(rows))
            else:
                # Fallback for categories without a clear table prefab (e.g. Identity, Skills as tags)
                cat_lines = []
                for f in fields:
                    val = get_path(player, f.path)
                    rendered = self._render_field(val, f.prefab)
                    if rendered:
                        cat_lines.append(f"{f.label}: {rendered}")
                if cat_lines:
                    sections.append(f"**{category.title()}**: " + ", ".join(cat_lines))

        return "\n\n".join(sections)

    def build_active_quests(self, session_id: int) -> str:
        """Renders active quests as a Markdown table."""
        try:
            quest_result = self.tools.execute(
                StateQuery(entity_type="quest", key="*", json_path="."),
                context={"session_id": session_id, "db_manager": self.db},
            )
            quests = quest_result.get("value", {}) or {}
            if quests and isinstance(quests, dict):
                active_q = [
                    f"| {q.get('title')} | {q.get('status')} | {q.get('goal', '')} |"
                    for q in quests.values()
                    if q.get("status") == "active"
                ]
                if active_q:
                    return "| Title | Status | Goal |\n| :--- | :--- | :--- |\n" + "\n".join(active_q)
        except Exception:
            pass
        return ""

    def build_scene_roster(self, session_id: int) -> str:
        """Renders currently present NPCs as a Markdown table."""
        scene = self.db.game_state.get_entity(session_id, "scene", "active_scene")
        if scene and "members" in scene:
            rows = []
            for member in scene["members"]:
                if "player" in member:
                    continue
                if ":" in member:
                    etype, ekey = member.split(":", 1)
                    ent = self.db.game_state.get_entity(session_id, etype, ekey)
                    if ent:
                        e_name = ent.get(FieldKey.NAME, "Unknown")
                        e_status = ent.get("disposition") or ent.get("role") or "Present"
                        rows.append(f"| `{ekey}` | {e_name} | {e_status} |")
            if rows:
                return "| Entity ID | Name | Role/Status |\n| :--- | :--- | :--- |\n" + "\n".join(rows)
        return ""

    def _render_field(self, value: Any, prefab: str) -> str:
        """Render value based on prefab type for the LLM Context."""
        if value is None:
            return ""

        if prefab == PrefabID.RES_POOL:
            # Render as Current/Max
            if isinstance(value, dict):
                curr = value.get(FieldKey.CURRENT, 0)
                mx = value.get(FieldKey.MAX, 0)
                return f"{curr}/{mx}"
            return str(value)

        elif prefab == PrefabID.RES_TRACK:
            # Render as visual dots: [x][x][ ]
            if isinstance(value, list):
                return "".join(["[x]" if x else "[ ]" for x in value])
            return str(value)

        elif prefab == PrefabID.VAL_COMPOUND:
            # Render as Score (+Mod)
            if isinstance(value, dict):
                score = value.get(FieldKey.SCORE, 0)
                mod = value.get(FieldKey.MOD, 0)
                sign = "+" if mod >= 0 else ""
                return f"{score} ({sign}{mod})"
            return str(value)

        elif prefab == PrefabID.VAL_LADDER:
            # Render as +1 (Average)
            if isinstance(value, dict):
                val = value.get(FieldKey.VALUE, 0)
                lbl = value.get(FieldKey.LABEL, "")
                sign = "+" if val >= 0 else ""
                return f"{sign}{val} ({lbl})"
            return str(value)

        elif prefab == PrefabID.CONT_LIST:
            # Concise list: [Sword, Shield]
            if isinstance(value, list):
                items = []
                for item in value:
                    if isinstance(item, dict):
                        name = item.get(FieldKey.NAME, "Item")
                        qty = item.get(FieldKey.QTY, 1)
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

        elif prefab == PrefabID.CONT_TAGS:
            if isinstance(value, list):
                return "[" + ", ".join(str(v) for v in value) + "]"
            return "[]"

        return str(value)

