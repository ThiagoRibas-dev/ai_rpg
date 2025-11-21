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
            if self.logger:
                self.logger.debug("StateContextBuilder: no session_id, skipping.")
            return ""

        lines: List[str] = []
        ctx = {"session_id": session_id, "db_manager": self.db}

        try:
            # 1. Load Player Entity
            player = get_entity(session_id, self.db, "character", "player")
            if not player:
                return "No character data found."

            # 2. Load StatBlockTemplate
            # (In a real implementation, we'd cache this or pass it in, but looking it up is safe for now)
            template_id = player.get("template_id")
            stat_template = None
            if template_id:
                stat_template = self.db.stat_templates.get_by_id(template_id)
            
            name = player.get("name", "Player")
            lines.append(f"**Player Character**: {name}")
            
            if not stat_template:
                 # Fallback for legacy/uninitialized
                 lines.append("(No stat template defined)")
                 return "\n".join(lines)

            # 3. Format Abilities
            # e.g. "Strength: 16", "Fight: d20"
            abilities_data = player.get("abilities", {})
            if stat_template.abilities:
                lines.append("**Abilities**:")
                attr_strs = []
                for ab_def in stat_template.abilities:
                    val = abilities_data.get(ab_def.name, ab_def.default)
                    # Add simple modifier hint ONLY for integer stats in standard D&D range (e.g. > 5)
                    # This is a heuristic to avoid showing "-4" for a 1-dot stat in Vampire.
                    if (ab_def.data_type == "integer" and 
                        isinstance(val, int) and 
                        val > 5 and val < 30): # Heuristic range for D20 systems
                        mod = (val - 10) // 2
                        val_str = f"{val} ({mod:+})"
                    else:
                        val_str = str(val)
                    attr_strs.append(f"{ab_def.name}: {val_str}")
                lines.append(", ".join(attr_strs))
                lines.append("")

            # 4. Format Vitals
            # e.g. "HP: 12/20"
            vitals_data = player.get("vitals", {})
            if stat_template.vitals:
                vital_strs = []
                for vit_def in stat_template.vitals:
                    # Vital data is stored as {current: X, max: Y} or just X
                    data = vitals_data.get(vit_def.name, {})
                    if isinstance(data, dict):
                        curr = data.get("current", 0)
                        mx = data.get("max", "?")
                    else:
                        curr = data
                        mx = "?" # Max usually derived, might need extra logic to fetch
                    vital_strs.append(f"{vit_def.name}: {curr}/{mx}")
                if vital_strs:
                    lines.append(f"**Vitals**: {', '.join(vital_strs)}")
                lines.append("")

            # 5. Format Tracks (Clocks)
            # e.g. "Stress: [X][X][ ][ ] (2/4)"
            tracks_data = player.get("tracks", {})
            if stat_template.tracks:
                for track_def in stat_template.tracks:
                    val = tracks_data.get(track_def.name, 0)
                    if isinstance(val, dict):
                        val = val.get("value", 0)
                    mx = track_def.max_value
                    # Visual representation
                    if mx < 15: # For things like spell slots
                        filled = "[ ]" * val
                        empty = "[x]" * (mx - val)
                        lines.append(f"**{track_def.name}**: {filled}{empty} ({val}/{mx})")
                    else: # Tracks like experience
                        lines.append(f"**{track_def.name}**: ({val}/{mx})")
                lines.append("")

            # 6. Format Slots (Inventory/Spells)
            slots_data = player.get("slots", {})
            for slot_def in stat_template.slots:
                items = slots_data.get(slot_def.name, [])
                if items:
                    lines.append(f"**{slot_def.name}** ({len(items)} items):")
                    for item in items[:5]: # Limit display
                        qty = item.get("quantity", 1)
                        qty_str = f" x{qty}" if qty > 1 else ""
                        lines.append(f"- {item['name']}{qty_str}")
                    if len(items) > 5:
                        lines.append(f"- ... and {len(items)-5} more")
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
                self.logger.debug(f"StateContextBuilder: failed to build state: {e}", exc_info=True)
            # fail silently into empty

        return "\n".join(lines) if lines else ""
