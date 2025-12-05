from nicegui import ui
from app.services.state_service import get_entity
import logging

logger = logging.getLogger(__name__)


class CharacterInspector:
    """
    Universal Character Sheet Renderer.
    Adapts to any CharacterSheetSpec structure.
    Includes defensive coding to handle LLM structure mismatches.
    """

    def __init__(self, db_manager):
        self.db = db_manager
        self.session_id = None
        self.container = None
        self.entity_key = "player"

    def set_session(self, session_id: int):
        self.session_id = session_id
        self.refresh()

    def refresh(self):
        if not self.container:
            return
        self.container.clear()

        if not self.session_id:
            with self.container:
                ui.label("No Session").classes("text-gray-500")
            return

        # 1. Fetch Entity & Template
        entity = get_entity(self.session_id, self.db, "character", self.entity_key)
        if not entity:
            return

        tid = entity.get("template_id")
        template = self.db.stat_templates.get_by_id(tid) if tid else None

        if not template:
            with self.container:
                ui.label("Legacy/No Template").classes("text-yellow-600")
            return

        # 2. Render Loop
        with self.container:
            self._render_header(entity, template)

            cats = [
                "attributes",
                "resources",
                "skills",
                "features",
                "inventory",
                "connections",
                "narrative",
            ]

            spec = (
                template.model_dump() if hasattr(template, "model_dump") else template
            )

            for cat_key in cats:
                if cat_key in spec:
                    self._render_category(
                        cat_key, spec[cat_key], entity.get(cat_key, {})
                    )

    def _render_header(self, entity, template):
        name = entity.get("name", "Unknown")
        identity = entity.get("identity", {})
        subtext = (
            identity.get("concept")
            or identity.get("occupation")
            or identity.get("background")
            or "Player Character"
        )

        with ui.row().classes("w-full items-center justify-between mb-2"):
            with ui.column().classes("gap-0"):
                ui.label(name).classes("text-2xl font-bold text-white leading-none")
                ui.label(subtext).classes("text-xs text-amber-400")
            ui.icon("person").classes("text-slate-600 text-4xl")

    def _render_category(self, cat_key, cat_def, cat_data):
        """Renders a whole category (e.g. Attributes)."""
        
        # DEFENSIVE: If data isn't a dict (e.g. legacy inventory list), skip
        if not isinstance(cat_data, dict):
            return

        fields = cat_def.get("fields", {})
        if not fields:
            return

        with ui.column().classes(
            "w-full mb-2 bg-slate-800/50 rounded border border-slate-700/50 p-2"
        ):
            ui.label(cat_key.title()).classes(
                "text-xs font-bold text-gray-500 uppercase mb-2"
            )

            for field_key, field_def in fields.items():
                self._render_field(field_key, field_def, cat_data)

    def _render_field(self, key, definition, data_source):
        container_type = definition.get("container_type", "atom")
        display = definition.get("display", {})
        label = display.get("label", key)
        widget = display.get("widget", "text")

        if container_type == "atom":
            val = data_source.get(key, definition.get("default", ""))

            with ui.row().classes("w-full justify-between items-center mb-1"):
                ui.label(label).classes("text-sm text-gray-300")

                if widget == "die":
                    ui.badge(str(val), color="purple").props("text-color=white")
                elif widget == "number":
                    ui.label(str(val)).classes("font-mono font-bold text-blue-300")
                elif widget == "toggle":
                    icon = "check_box" if val else "check_box_outline_blank"
                    ui.icon(icon).classes("text-green-400" if val else "text-gray-600")
                else:
                    ui.label(str(val)).classes("text-sm text-gray-400")

        elif container_type == "molecule":
            val_obj = data_source.get(key, {})

            # DEFENSIVE: If we expect a molecule (dict) but got a primitive (int/str)
            # This happens if LLM ignored structure prompts.
            if not isinstance(val_obj, dict):
                val_obj = {"current": val_obj, "max": val_obj, "value": val_obj}

            if widget == "pool":
                curr = val_obj.get("current", 0)
                mx = val_obj.get("max", 10)
                pct = max(0, min(1, curr / mx)) if mx > 0 else 0

                with ui.column().classes("w-full mb-2"):
                    with ui.row().classes("w-full justify-between text-xs"):
                        ui.label(label).classes("font-bold")
                        ui.label(f"{curr} / {mx}")
                    ui.linear_progress(value=pct, size="8px", show_value=False).classes(
                        "rounded"
                    )

            elif widget == "track":
                val = val_obj.get("value", 0)
                length = 5 # Default
                
                with ui.row().classes("w-full justify-between items-center mb-1"):
                    ui.label(label).classes("text-sm")
                    with ui.row().classes("gap-1"):
                        for i in range(length):
                            icon = (
                                "circle" if i < val else "circle_notifications"
                            )
                            color = "text-red-400" if i < val else "text-gray-700"
                            ui.icon("circle").classes(f"text-[10px] {color}")

        elif container_type == "list":
            items = data_source.get(key, [])
            
            # DEFENSIVE: If items isn't a list (e.g. dict or None), handle gracefully
            if not isinstance(items, list):
                items = []

            with ui.expansion(f"{label} ({len(items)})", icon="list").classes(
                "w-full bg-slate-900 rounded mb-1"
            ):
                if not items:
                    ui.label("Empty").classes("text-xs text-gray-600 p-2")
                else:
                    with ui.column().classes("w-full gap-1 p-2"):
                        for item in items:
                            # Try to find a 'name' or 'label' key
                            item_name = (
                                item.get("name")
                                or item.get("label")
                                or next(iter(item.values()))
                            )
                            ui.label(str(item_name)).classes(
                                "text-xs text-gray-300 border-b border-slate-800 w-full pb-1"
                            )

    def render(self):
        self.container = ui.column().classes("w-full p-2")
        self.refresh()