from nicegui import ui
from app.services.state_service import get_entity
from app.setup.setup_manifest import SetupManifest
from app.prefabs.validation import get_path
from app.gui.controls.field_editor import FieldEditorDialog
from typing import Any


class InventoryInspector:
    def __init__(self, db_manager, orchestrator):
        self.db = db_manager
        self.orchestrator = orchestrator
        self.session_id = None
        self.container = None

    def set_session(self, session_id: int):
        self.session_id = session_id
        self.refresh()

    def refresh(self):
        if not self.container:
            return
        self.container.clear()

        if not self.session_id:
            with self.container:
                ui.label("No Session").classes("text-gray-500 italic")
            return

        entity = get_entity(self.session_id, self.db, "character", "player")
        if not entity:
            return

        # Fetch Manifest
        setup_data = SetupManifest(self.db).get_manifest(self.session_id)
        manifest_id = setup_data.get("manifest_id")
        manifest = self.db.manifests.get_by_id(manifest_id) if manifest_id else None

        # Find list fields
        lists_to_render = []  # (label, items)

        if manifest:
            # Look for CONT_LIST or CONT_WEIGHTED
            for f in manifest.fields:
                if f.prefab in ["CONT_LIST", "CONT_WEIGHTED"]:
                    items = get_path(entity, f.path)
                    if isinstance(items, list):
                        lists_to_render.append((f.label, items))
        else:
            # Fallback
            inv = entity.get("inventory", {})
            if isinstance(inv, dict):
                for k, v in inv.items():
                    if isinstance(v, list):
                        lists_to_render.append((k.title(), v))

        # Render
        with self.container:
            if not lists_to_render:
                ui.label("No Inventory Lists Found").classes("text-gray-500 italic")
                return

            for label, items in lists_to_render:
                # Find the path for this collection to allow adding items
                collection_path = next((f.path for f in manifest.fields if f.label == label), None) if manifest else None
                self._render_collection(label, items, collection_path)

    def _render_collection(self, title, items, path=None):
        with (
            ui.expansion(f"{title} ({len(items)})", icon="backpack")
            .classes("w-full bg-slate-800/50 rounded mb-2 border border-slate-700/50")
            .props("default-opened")
        ):
            if path:
                with ui.row().classes("w-full justify-end p-1"):
                    ui.button("Add Item", icon="add", on_click=lambda p=path: self._prompt_add_item(p)).props("flat dense size=sm").classes("text-green-500")

            if not items:
                ui.label("Empty").classes("text-gray-500 italic text-sm p-2")
                return

            with ui.column().classes("w-full gap-1 p-2"):
                for idx, item in enumerate(items):
                    self._render_inventory_item(path, idx, item)

    def _render_inventory_item(self, path, idx, item):
        name = item.get("name", "Unknown") if isinstance(item, dict) else str(item)
        
        with ui.row().classes(
            "w-full justify-between items-center bg-slate-900/80 p-2 rounded border border-slate-700 group hover:border-slate-500 transition-colors relative"
        ):
            # Name
            ui.label(name).classes("font-bold text-gray-200 text-sm")

            # Right Side: Qty/Weight OR Actions
            with ui.row().classes("items-center gap-2"):
                # Info Stats (Visible unless hovered, but we can keep them visible and push actions to far right)
                if isinstance(item, dict):
                    extras = []
                    if item.get("qty", 1) > 1:
                        extras.append(f"x{item['qty']}")
                    if item.get("weight", 0) > 0:
                        extras.append(f"{item.get('weight', 0)}lb")

                    if extras:
                        ui.label(", ".join(extras)).classes("text-xs text-blue-400 font-mono")

                # Hover Actions Container
                # We use absolute positioning or just a flex row that appears
                with ui.row().classes("opacity-0 group-hover:opacity-100 transition-opacity bg-slate-900 rounded px-1 gap-1 border border-slate-700 shadow-xl"):
                    # Gameplay Actions
                    ui.button(icon="play_arrow", on_click=lambda: self.trigger_action("use", name)) \
                        .props("flat dense round size=xs color=green").tooltip(f"Use/Equip {name}")
                    
                    ui.button(icon="vertical_align_bottom", on_click=lambda: self.trigger_action("drop", name)) \
                        .props("flat dense round size=xs color=orange").tooltip(f"Drop {name}")
                    
                    ui.button(icon="help_outline", on_click=lambda: self.trigger_action("inspect", name)) \
                        .props("flat dense round size=xs color=cyan").tooltip(f"Inspect {name}")

                    # Meta Actions (Edit/Remove) - Only if path exists
                    if path:
                        ui.separator().props("vertical")
                        ui.button(icon="edit", on_click=lambda: self._edit_item(path, idx, item)) \
                            .props("flat dense round size=xs color=grey").tooltip("Edit (Manual)")
                        
                        ui.button(icon="delete", on_click=lambda: self._remove_item(path, idx)) \
                            .props("flat dense round size=xs color=red").tooltip("Remove (Manual)")

    def _edit_item(self, path, index, current_val):
        """Open editor for a specific item in a list."""
        # Using a special prefab or just VAL_TEXT for now? 
        # Actually, let's pass it to FieldEditorDialog as a dict/json for now
        FieldEditorDialog(
            label=f"Edit Item #{index+1}",
            path=f"{path}[{index}]",
            prefab="VAL_JSON", # Use fallback text area for the dict
            current_value=current_val,
            on_save=lambda p, v: self._handle_item_save(path, index, v)
        ).open()

    def _prompt_add_item(self, path):
        """Show dialog to add a new item."""
        new_item = {"name": "New Item", "qty": 1, "weight": 1.0}
        FieldEditorDialog(
            label="Add New Item",
            path=path,
            prefab="VAL_JSON",
            current_value=new_item,
            on_save=lambda p, v: self._handle_item_add(path, v)
        ).open()

    def _handle_item_save(self, path: str, index: int, new_val: Any):
        if not self.session_id:
            return
        entity = get_entity(self.session_id, self.db, "character", "player")
        items = get_path(entity, path)
        if isinstance(items, list) and index < len(items):
            items[index] = new_val
            self._update_collection(path, items)

    def _handle_item_add(self, path: str, new_val: Any):
        if not self.session_id:
            return
        entity = get_entity(self.session_id, self.db, "character", "player")
        items = get_path(entity, path) or []
        if isinstance(items, list):
            items.append(new_val)
            self._update_collection(path, items)

    def _remove_item(self, path: str, index: int):
        if not self.session_id:
            return
        entity = get_entity(self.session_id, self.db, "character", "player")
        items = get_path(entity, path)
        if isinstance(items, list) and index < len(items):
            items.pop(index)
            self._update_collection(path, items)

    def _update_collection(self, path: str, new_list: list):
        from app.services.manual_edit_service import ManualEditService
        service = ManualEditService(self.db, self.orchestrator.tool_registry, self.orchestrator.vector_store)
        result = service.update_field(
            session_id=self.session_id,
            entity_type="character",
            entity_key="player",
            path=path,
            new_value=new_list
        )
        if result.get("success"):
            ui.notify("Inventory updated")
            self.refresh()
        else:
            ui.notify(result.get("error"), type="negative")

    def trigger_action(self, verb: str, item_name: str):
        if not self.session_id or not self.orchestrator:
            return
        game_session = self.db.sessions.get_by_id(self.session_id)
        if not game_session:
            return

        command = f"I {verb} the {item_name}."
        self.orchestrator.bridge._last_input = command
        ui.notify(f"Action: {command}")

        if self.orchestrator.bridge.chat_component:
            self.orchestrator.bridge.chat_component.set_generating(True)

        self.orchestrator.plan_and_execute(game_session)
