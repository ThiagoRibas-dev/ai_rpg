from nicegui import ui
from app.services.state_service import get_entity
from app.setup.setup_manifest import SetupManifest
from app.prefabs.validation import get_path
import logging

logger = logging.getLogger(__name__)


class CharacterInspector:
    """
    Universal Character Sheet Renderer.
    Adapts to SystemManifest (Lego Protocol).
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

        # 1. Fetch Entity
        entity = get_entity(self.session_id, self.db, "character", self.entity_key)
        if not entity:
            return

        # 2. Fetch Manifest (Source of Truth)
        setup_data = SetupManifest(self.db).get_manifest(self.session_id)
        manifest_id = setup_data.get("manifest_id")
        manifest = None

        if manifest_id:
            manifest = self.db.manifests.get_by_id(manifest_id)

        if not manifest:
            with self.container:
                ui.label("No System Manifest Found").classes("text-red-400 italic")
            return

        # 3. Render Loop
        with self.container:
            self._render_header(entity, manifest)

            std_order = [
                "attributes",
                "resources",
                "combat",
                "status",
                "skills",
                "features",
                "inventory",
                "narrative",
                "progression",
            ]
            man_cats = manifest.get_categories()
            sorted_cats = [c for c in std_order if c in man_cats] + [
                c for c in man_cats if c not in std_order
            ]

            for cat_key in sorted_cats:
                if cat_key in ["meta", "identity"]:
                    continue

                fields = manifest.get_fields_by_category(cat_key)
                if fields:
                    self._render_category(cat_key, fields, entity)

    def _render_header(self, entity, manifest):
        name = entity.get("name", "Unknown")
        identity = entity.get("identity", {})
        concept = (
            identity.get("concept")
            or identity.get("class")
            or identity.get("archetype")
            or "Player Character"
        )

        with ui.row().classes("w-full items-center justify-between mb-2"):
            with ui.column().classes("gap-0"):
                ui.label(name).classes("text-2xl font-bold text-white leading-none")
                ui.label(concept).classes("text-xs text-amber-400")
                ui.label(manifest.name).classes("text-[10px] text-slate-500")
            ui.icon("person").classes("text-slate-600 text-4xl")

    def _render_category(self, cat_key, fields, entity):
        with ui.column().classes(
            "w-full mb-2 bg-slate-800/50 rounded border border-slate-700/50 p-2"
        ):
            ui.label(cat_key.title()).classes(
                "text-xs font-bold text-gray-500 uppercase mb-2"
            )

            for field_def in fields:
                self._render_field(field_def, entity)

    def _render_field(self, field_def, entity):
        val = get_path(entity, field_def.path)
        prefab = field_def.prefab
        label = field_def.label

        # --- VAL FAMILY ---
        if prefab.startswith("VAL_"):
            
            if prefab == "VAL_TEXT":
                with ui.row().classes("w-full justify-between items-center mb-1"):
                    ui.label(label).classes("text-sm text-gray-300")
                    ui.label(str(val)).classes("text-sm text-white font-serif italic")
            
            elif prefab == "VAL_INT":
                with ui.row().classes("w-full justify-between items-center mb-1"):
                    ui.label(label).classes("text-sm text-gray-300")
                    ui.label(str(val)).classes("font-mono font-bold text-blue-300")

            elif prefab == "VAL_COMPOUND":
                with ui.row().classes("w-full justify-between items-center mb-1"):
                    ui.label(label).classes("text-sm text-gray-300")
                    if isinstance(val, dict):
                        score = val.get("score", 0)
                        mod = val.get("mod", 0)
                        sign = "+" if mod >= 0 else ""
                        ui.label(f"{score} ({sign}{mod})").classes(
                            "font-mono text-amber-300"
                        )
                    else:
                        ui.label(str(val))

            elif prefab == "VAL_STEP_DIE":
                with ui.row().classes("w-full justify-between items-center mb-1"):
                    ui.label(label).classes("text-sm text-gray-300")
                    ui.badge(str(val), color="purple").props("text-color=white")

            elif prefab == "VAL_BOOL":
                with ui.row().classes("w-full justify-between items-center mb-1"):
                    ui.label(label).classes("text-sm text-gray-300")
                    icon = "check_box" if val else "check_box_outline_blank"
                    color = "text-green-400" if val else "text-gray-600"
                    ui.icon(icon).classes(color)

            elif prefab == "VAL_LADDER":
                with ui.row().classes("w-full justify-between items-center mb-1"):
                    ui.label(label).classes("text-sm text-gray-300")
                    if isinstance(val, dict):
                        v = val.get("value", 0)
                        lbl = val.get("label", "")
                        sign = "+" if v >= 0 else ""
                        ui.label(f"{sign}{v} {lbl}").classes("text-sm text-cyan-300")
                    else:
                        ui.label(str(val))

        # --- RES FAMILY ---
        elif prefab == "RES_POOL":
            if not isinstance(val, dict):
                val = {"current": 0, "max": 0}
            curr = val.get("current", 0)
            mx = val.get("max", 0)
            pct = max(0, min(1, curr / mx)) if mx > 0 else 0

            with ui.column().classes("w-full mb-2"):
                with ui.row().classes("w-full justify-between text-xs"):
                    ui.label(label).classes("font-bold")
                    ui.label(f"{curr} / {mx}")
                ui.linear_progress(value=pct, size="8px", show_value=False).classes(
                    "rounded"
                )

        elif prefab == "RES_TRACK":
            if not isinstance(val, list):
                val = []
            with ui.row().classes("w-full justify-between items-center mb-1"):
                ui.label(label).classes("text-sm")
                with ui.row().classes("gap-1"):
                    for state in val:
                        icon = "circle" if state else "circle_notifications"
                        color = "text-red-400" if state else "text-gray-700"
                        ui.icon("circle").classes(f"text-[10px] {color}")

        elif prefab == "RES_COUNTER":
            with ui.row().classes("w-full justify-between items-center mb-1"):
                ui.label(label).classes("text-sm text-gray-300")
                ui.label(str(val)).classes("font-mono text-green-400")

        # --- CONT FAMILY ---
        elif prefab in ["CONT_LIST", "CONT_TAGS", "CONT_WEIGHTED"]:
            count = len(val) if isinstance(val, list) else 0
            with ui.expansion(f"{label} ({count})", icon="list").classes(
                "w-full bg-slate-900 rounded mb-1"
            ):
                if not val or not isinstance(val, list):
                    ui.label("Empty").classes("text-xs text-gray-600 p-2")
                else:
                    with ui.column().classes("w-full gap-1 p-2"):
                        for item in val:
                            txt = ""
                            if isinstance(item, dict):
                                txt = f"{item.get('name', '???')}"
                                if item.get("qty", 1) > 1:
                                    txt += f" (x{item['qty']})"
                            else:
                                txt = str(item)

                            ui.label(txt).classes(
                                "text-xs text-gray-300 border-b border-slate-800 w-full pb-1"
                            )

    def render(self):
        self.container = ui.column().classes("w-full p-2")
        self.refresh()
