from nicegui import ui
from app.services.state_service import get_entity
from app.setup.setup_manifest import SetupManifest
from app.prefabs.validation import get_path
from app.gui.controls.field_editor import FieldEditorDialog
from typing import Any
import logging

logger = logging.getLogger(__name__)


class CharacterInspector:
    """
    Universal Character Sheet Renderer.
    Adapts to SystemManifest (Lego Protocol).
    """

    def __init__(self, db_manager, orchestrator):
        self.db = db_manager
        self.orchestrator = orchestrator
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
        path = field_def.path
        is_derived = bool(field_def.formula)

        # Base item class with hover and cursor
        row_classes = "w-full justify-between items-center mb-1 rounded p-1 transition-colors "
        if not is_derived:
            row_classes += "cursor-pointer hover:bg-slate-700/40 group"
        else:
            row_classes += "opacity-80"

        # Editor trigger
        def on_click():
            if not is_derived:
                FieldEditorDialog(
                    label=label,
                    path=path,
                    prefab=prefab,
                    current_value=val,
                    on_save=self._handle_field_save,
                ).open()
            else:
                ui.notify(f"{label} is calculated automatically.", type="info")

        # --- VAL FAMILY ---
        if prefab.startswith("VAL_"):
            with ui.row().classes(row_classes).on("click", on_click):
                ui.label(label).classes("text-sm text-gray-300")
                
                with ui.row().classes("items-center gap-2"):
                    if is_derived:
                        ui.icon("functions", size="12px").classes("text-slate-500")

                    if prefab == "VAL_TEXT":
                        ui.label(str(val)).classes("text-sm text-white font-serif italic")
                    elif prefab == "VAL_INT":
                        ui.label(str(val)).classes("font-mono font-bold text-blue-300")
                    elif prefab == "VAL_COMPOUND":
                        if isinstance(val, dict):
                            score = val.get("score", 0)
                            mod = val.get("mod", 0)
                            sign = "+" if mod >= 0 else ""
                            ui.label(f"{score} ({sign}{mod})").classes("font-mono text-amber-300")
                        else:
                            ui.label(str(val))
                    elif prefab == "VAL_STEP_DIE":
                        ui.badge(str(val), color="purple").props("text-color=white")
                    elif prefab == "VAL_BOOL":
                        icon = "check_box" if val else "check_box_outline_blank"
                        color = "text-green-400" if val else "text-gray-600"
                        ui.icon(icon).classes(color)
                    elif prefab == "VAL_LADDER":
                        if isinstance(val, dict):
                            v = val.get("value", 0)
                            lbl = val.get("label", "")
                            sign = "+" if v >= 0 else ""
                            ui.label(f"{sign}{v} {lbl}").classes("text-sm text-cyan-300")
                        else:
                            ui.label(str(val))

                    if not is_derived:
                        ui.icon("edit", size="12px").classes("text-slate-600 opacity-0 group-hover:opacity-100")

        # --- RES FAMILY ---
        elif prefab == "RES_POOL":
            if not isinstance(val, dict):
                val = {"current": 0, "max": 0}
            curr = val.get("current", 0)
            mx = val.get("max", 0)
            pct = max(0, min(1, curr / mx)) if mx > 0 else 0

            with ui.column().classes("w-full mb-2"):
                with ui.row().classes("w-full justify-between items-center text-xs mb-1"):
                    with ui.row().classes("items-center gap-1 cursor-pointer").on("click", on_click):
                        ui.label(label).classes("font-bold text-gray-300")
                        if field_def.max_formula:
                            ui.icon("functions", size="10px").classes("text-slate-500")
                        ui.icon("edit", size="10px").classes("text-slate-600 opacity-0 group-hover:opacity-100")

                    # Quick +/- Buttons
                    with ui.row().classes("items-center gap-1 bg-slate-800/50 rounded px-1"):
                        ui.button("-", on_click=lambda p=path: self._quick_adjust(p, -1)).props("flat dense round size=xs color=red")
                        ui.label(f"{curr} / {mx}").classes("min-w-[40px] text-center font-mono")
                        ui.button("+", on_click=lambda p=path: self._quick_adjust(p, 1)).props("flat dense round size=xs color=green")

                ui.linear_progress(value=pct, size="6px", show_value=False).classes("rounded bg-slate-700")

        elif prefab == "RES_TRACK":
            if not isinstance(val, list):
                val = []
            with ui.row().classes(row_classes).on("click", on_click):
                ui.label(label).classes("text-sm text-gray-300")
                with ui.row().classes("gap-1"):
                    for state in val:
                        color = "text-red-500" if state else "text-slate-700"
                        ui.icon("circle").classes(f"text-[10px] {color}")

        elif prefab == "RES_COUNTER":
            with ui.row().classes(row_classes).on("click", on_click):
                ui.label(label).classes("text-sm text-gray-300")
                with ui.row().classes("items-center gap-2"):
                    # Quick adjust for counters too
                    ui.button("-", on_click=lambda p=path: self._quick_adjust(p, -1)).props("flat dense round size=xs")
                    ui.label(str(val)).classes("font-mono font-bold text-green-400 min-w-[20px] text-center")
                    ui.button("+", on_click=lambda p=path: self._quick_adjust(p, 1)).props("flat dense round size=xs")

        # --- CONT FAMILY ---
        elif prefab in ["CONT_LIST", "CONT_TAGS", "CONT_WEIGHTED"]:
            count = len(val) if isinstance(val, list) else 0
            with ui.expansion(f"{label} ({count})", icon="list").classes(
                "w-full bg-slate-900 rounded mb-1"
            ):
                # Add Item Button
                with ui.row().classes("w-full justify-end p-1 border-b border-slate-800"):
                    ui.button("Add", icon="add", on_click=lambda p=path: self._prompt_add_item(p)).props("flat dense size=xs color=green")

                if not val or not isinstance(val, list):
                    ui.label("Empty").classes("text-xs text-gray-600 p-2")
                else:
                    with ui.column().classes("w-full gap-1 p-2"):
                        for idx, item in enumerate(val):
                            self._render_list_item(path, idx, item)

    def _render_list_item(self, path, idx, item):
        txt = ""
        if isinstance(item, dict):
            txt = f"{item.get('name', '???')}"
            if item.get("qty", 1) > 1:
                txt += f" (x{item['qty']})"
        else:
            txt = str(item)

        with ui.row().classes(
            "w-full justify-between items-center group hover:bg-slate-800 rounded px-1 transition-colors relative"
        ):
            ui.label(txt).classes("text-xs text-gray-300 py-1")
            
            # Hover Actions (Edit/Delete) - Absolute positioned to the right or just flex-end
            with ui.row().classes("opacity-0 group-hover:opacity-100 transition-opacity bg-slate-800 rounded px-1 gap-1"):
                ui.button(icon="edit", on_click=lambda: self._edit_list_item(path, idx, item)).props("flat dense round size=xs color=grey")
                ui.button(icon="delete", on_click=lambda: self._delete_list_item(path, idx)).props("flat dense round size=xs color=red")

    def _handle_field_save(self, path: str, new_value: Any):
        """Callback when a field is saved via the editor."""
        if not self.session_id:
            ui.notify("No session active", type="negative")
            return

        from app.services.manual_edit_service import ManualEditService

        service = ManualEditService(
            self.db,
            self.orchestrator.tool_registry,
            self.orchestrator.vector_store,
        )

        result = service.update_field(
            session_id=self.session_id,
            entity_type="character",
            entity_key=self.entity_key,
            path=path,
            new_value=new_value,
        )

        if result.get("success"):
            ui.notify(f"✓ {result.get('message')}", type="positive")
            # Clear cache and refresh
            self.refresh()
        else:
            ui.notify(f"✗ {result.get('error')}", type="negative")

    def _quick_adjust(self, path: str, delta: int):
        """Quickly adjust a resource current value."""
        if not self.session_id:
            return

        # Fetch current entity stats
        entity = get_entity(self.session_id, self.db, "character", self.entity_key)
        if not entity:
            return

        full_val = get_path(entity, path)
        if isinstance(full_val, dict) and "current" in full_val:
            # It's a pool, adjust the current value
            new_val = full_val.get("current", 0) + delta
            self._handle_field_save(f"{path}.current", new_val)
        else:
            # It's a simple int or counter
            new_val = int(full_val or 0) + delta
            self._handle_field_save(path, new_val)

    def _prompt_add_item(self, path):
        """Show dialog to add a new item/tag."""
        try:
            logger.debug(f"Prompting add item for path: {path}")
            new_val = {"name": "New Item", "description": ""} 
            
            FieldEditorDialog(
                label="Add New Item",
                path=path,
                prefab="VAL_JSON",
                current_value=new_val,
                on_save=lambda p, v: self._handle_list_add(p, v)
            ).open()
        except Exception as e:
            logger.error(f"Error in _prompt_add_item: {e}", exc_info=True)
            ui.notify(f"Error: {e}", type="negative")

    def _edit_list_item(self, path, index, current_val):
        try:
            logger.debug(f"Editing list item: {path}[{index}]")
            # ui.notify("Opening editor...", type="info", timeout=1000) # Optional debug
            FieldEditorDialog(
                label="Edit Item",
                path=f"{path}[{index}]",
                prefab="VAL_JSON",
                current_value=current_val,
                on_save=lambda p, v: self._handle_list_update(path, index, v)
            ).open()
        except Exception as e:
            logger.error(f"Error in _edit_list_item: {e}", exc_info=True)
            ui.notify(f"Error: {e}", type="negative")

    def _handle_list_add(self, path, new_item):
        try:
            if not self.session_id:
                return
            entity = get_entity(self.session_id, self.db, "character", self.entity_key)
            items = get_path(entity, path)
            if items is None:
                items = []
            if isinstance(items, list):
                items.append(new_item)
                self._handle_field_save(path, items)
        except Exception as e:
            logger.error(f"Error in _handle_list_add: {e}", exc_info=True)
            ui.notify(f"Save Error: {e}", type="negative")

    def _handle_list_update(self, path, index, new_item):
        try:
            if not self.session_id:
                return
            entity = get_entity(self.session_id, self.db, "character", self.entity_key)
            items = get_path(entity, path)
            if isinstance(items, list) and 0 <= index < len(items):
                items[index] = new_item
                self._handle_field_save(path, items)
        except Exception as e:
            logger.error(f"Error in _handle_list_update: {e}", exc_info=True)
            ui.notify(f"Save Error: {e}", type="negative")

    def _delete_list_item(self, path, index):
        try:
            if not self.session_id:
                return
            entity = get_entity(self.session_id, self.db, "character", self.entity_key)
            items = get_path(entity, path)
            if isinstance(items, list) and 0 <= index < len(items):
                items.pop(index)
                self._handle_field_save(path, items)
        except Exception as e:
            logger.error(f"Error in _delete_list_item: {e}", exc_info=True)
            ui.notify(f"Delete Error: {e}", type="negative")

    def render(self):
        self.container = ui.column().classes("w-full p-2")
        self.refresh()
