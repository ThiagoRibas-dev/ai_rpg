import logging
from typing import Any

from app.models.vocabulary import FieldKey
from app.prefabs.manifest import SystemManifest
from app.prefabs.validation import get_path
from app.services.state_service import get_entity
from app.tools.registry import ToolRegistry
from app.tools.schemas import StateQuery


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
        """Renders character fields into a clean JSON structure."""
        import json
        player = get_entity(session_id, self.db, "character", "player")
        if not player:
            return "No character data found."

        sheet: dict[str, Any] = {}

        for category in manifest.get_categories():
            fields = manifest.get_fields_by_category(category)
            if not fields:
                continue

            # Ensure category dict exists
            if category not in sheet:
                sheet[category] = {}

            for f in fields:
                # The path gives us the key under the category (e.g., 'str' for 'attributes.str')
                # For paths like 'resources.hp', category='resources', key='hp'
                path_parts = f.path.split('.')
                if len(path_parts) > 1 and path_parts[0] == category:
                    key = path_parts[1]
                else:
                    # fallback if path doesn't strictly match category (should not happen based on schema)
                    key = path_parts[-1]

                val = get_path(player, f.path)

                # Clone value to avoid modifying the entity directly
                import copy
                cloned_val = copy.deepcopy(val)

                # Attach _label
                if isinstance(cloned_val, dict):
                    cloned_val["_label"] = f.label
                elif isinstance(cloned_val, list):
                    # Wrap list if it's top-level
                    cloned_val = {"_label": f.label, "items": cloned_val}
                else:
                    cloned_val = {"_label": f.label, "value": cloned_val}

                sheet[category][key] = cloned_val

        return json.dumps(sheet, indent=2)

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

