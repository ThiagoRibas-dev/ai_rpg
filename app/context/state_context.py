import logging
from typing import List
from app.tools.registry import ToolRegistry
from app.tools.schemas import StateQuery
from app.tools.builtin._state_storage import get_entity
from app.utils.stat_renderer import render_stat_from_model
from app.utils.stat_renderer import render_stat_string


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

            # --- NEW: Load Template for Formatting ---
            template = None
            tid = player.get("template_id")
            if tid:
                template = self.db.stat_templates.get_by_id(tid)
            # ---------------------------------------

            name = player.get("name", "Player")
            lines.append(f"**Player Character**: {name}")

            # 2. Fundamentals (Inputs)
            fundamentals = player.get("fundamentals", {})
            if fundamentals:
                lines.append("**Attributes & Inputs**:")
                fund_strs = []
                for k, v in fundamentals.items():
                    # Format value based on template
                    display_val = str(v)
                    if template and k in template.fundamentals:
                        display_val = render_stat_from_model(
                            v, template.fundamentals[k]
                        )

                    fund_strs.append(f"{k}: {display_val}")
                lines.append(", ".join(fund_strs))
                lines.append("")

            # 3. Derived (Outputs)
            derived = player.get("derived", {})
            if derived:
                lines.append("**Combat & Stats**:")
                der_strs = []
                for k, v in derived.items():
                    # Format value based on template
                    display_val = str(v)
                    if template and k in template.derived:
                        display_val = render_stat_from_model(v, template.derived[k])

                    der_strs.append(f"{k}: {display_val}")
                lines.append(", ".join(der_strs))
                lines.append("")

            # 4. Gauges (Resources)
            gauges = player.get("gauges", {})
            if gauges:
                lines.append("**Vitals**:")
                vital_strs = []
                for k, v in gauges.items():
                    # Check template for labels
                    label = k
                    if template and k in template.gauges:
                        label = template.gauges[k].label

                    if isinstance(v, dict):
                        curr = v.get("current", 0)
                        mx = v.get("max", "?")
                        vital_strs.append(f"{label}: {curr}/{mx}")
                    else:
                        vital_strs.append(f"{label}: {v}")
                lines.append(", ".join(vital_strs))
                lines.append("")

            # 4b. Tracks (e.g. Stress)
            # Tracks are stored in 'tracks' or sometimes mixed in fundamentals in early versions
            # We assume 'tracks' key for cleaner separation, or check template
            tracks = player.get(
                "tracks", {}
            )  # Ensure your entity_update tool supports this key if used
            if template and template.tracks:
                track_strs = []
                for k, def_ in template.tracks.items():
                    # Try to find value in tracks, fallback to fundamentals
                    val = tracks.get(k, fundamentals.get(k, 0))

                    # Visual representation for LLM: [x][x][ ][ ]
                    length = def_.length
                    filled = min(length, max(0, int(val)))
                    visual = "[" + "X" * filled + "_" * (length - filled) + "]"

                    track_strs.append(f"{def_.label}: {visual} ({val}/{length})")

                if track_strs:
                    lines.append("**Tracks**:")
                    lines.append(", ".join(track_strs))
                    lines.append("")

            # 5. Collections (Inventory, Skills, etc)
            cols = player.get("collections", {})
            for col_id, items in cols.items():
                if not items:
                    continue

                # Get nicer label from template
                col_label = col_id.replace("_", " ").title()
                if template and col_id in template.collections:
                    col_label = template.collections[col_id].label

                lines.append(f"**{col_label}** ({len(items)}):")
                item_strs = []
                for item in items[:10]:  # Increased limit slightly
                    name = item.get("name", "???")
                    qty = item.get("qty", 1)

                    # Check for extra relevant fields from schema (e.g. "Rank" for skills)
                    extras = []
                    if template and col_id in template.collections:
                        schema = template.collections[col_id].item_schema
                        for field in schema:
                            if field.key not in ["name", "qty"] and field.key in item:
                                # Render specific fields like dice or bonuses inside list items
                                raw_val = item[field.key]
                                fmt_val = render_stat_string(raw_val, field.widget)
                                extras.append(f"{field.label}: {fmt_val}")

                    extra_str = f" [{', '.join(extras)}]" if extras else ""
                    qty_str = f" (x{qty})" if qty > 1 else ""

                    item_strs.append(f"{name}{qty_str}{extra_str}")

                lines.append(", ".join(item_strs))
                if len(items) > 10:
                    lines.append(f"...and {len(items) - 10} more.")
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
                self.logger.warning(f"State build failed: {e}", exc_info=True)

        return "\n".join(lines)
