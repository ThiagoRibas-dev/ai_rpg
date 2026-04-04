from __future__ import annotations

from typing import TYPE_CHECKING, Any

from nicegui import ui

from app.models.vocabulary import CategoryName, PrefabID
from app.prefabs.validation import get_path
from app.services.manual_edit_service import ManualEditService
from app.services.state_service import get_entity
from app.setup.setup_manifest import SetupManifest

from .rendering_mixin import RenderingMixin

if TYPE_CHECKING:
    from app.core.orchestrator import Orchestrator
    from app.database.db_manager import DBManager


class InventoryInspector(RenderingMixin):
    def __init__(self, db_manager: DBManager, orchestrator: Orchestrator):
        self.db = db_manager
        self.orchestrator = orchestrator
        self.session_id: int | None = None
        self.container: ui.column | None = None
        self.entity_key: str = "player"

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

        if not self.db:
            return
        entity = get_entity(self.session_id, self.db, "character", "player")
        if not entity:
             with self.container:
                 ui.label("Character 'player' not found.").classes("text-gray-500 italic")
             return

        # Fetch Manifest
        setup_data = SetupManifest(self.db).get_manifest(self.session_id)
        manifest_id = setup_data.get("manifest_id")
        manifest = self.db.manifests.get_by_id(manifest_id) if manifest_id and self.db.manifests else None

        # Find list fields
        lists_to_render = []  # (label, items)

        if manifest:
            # Look for CONT_LIST or CONT_WEIGHTED
            for f in manifest.fields:
                is_list = f.prefab in [PrefabID.CONT_LIST, PrefabID.CONT_WEIGHTED]
                is_inv = f.category == CategoryName.INVENTORY or f.path.startswith("inventory")
                if is_list and is_inv:
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
                field_def = next((f for f in manifest.fields if f.label == label), None) if manifest else None
                collection_path = field_def.path if field_def else None
                config = field_def.config if field_def else None
                self._render_collection(label, items, collection_path, config)

    def _render_collection(self, title, items, path=None, config=None):
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
                    self._render_inventory_item(path, idx, item, config)

    def _render_inventory_item(self, path, idx, item, config=None):
        item_path = f"{path}.{idx}" if path else None
        name = self._get_item_label(item, config)

        # 3-Layer Agnostic Prefab Detection for List Items
        detected_prefab, key_map = self._detect_item_prefab(item, config)
        if detected_prefab == PrefabID.RES_POOL:
            pool_keys = (key_map.get("curr_key"), key_map.get("max_key"))
        else:
            pool_keys = (None, None)

        with ui.row().classes(
            "w-full justify-between items-center bg-slate-900/80 p-2 rounded border border-slate-700 group hover:border-slate-500 transition-colors relative"
        ):
            # Content Column
            with ui.column().classes("flex-grow gap-0"):
                if detected_prefab == PrefabID.RES_POOL and item_path:
                    self._render_pool_widget(name, item_path, item, config, mini=True, keys=pool_keys)
                elif detected_prefab == PrefabID.RES_TRACK and item_path:
                    self._render_track_widget(name, item_path, item, config, mini=True)
                elif detected_prefab == PrefabID.RES_COUNTER and item_path:
                    self._render_counter_widget(name, item_path, item, config, mini=True)
                else:
                    ui.label(name).classes("font-bold text-gray-200 text-sm")
                    # Fallback text summary for other keys
                    summary = self._format_item_agnostic(item, config)
                    if summary != name and summary != "???":
                         ui.label(summary).classes("text-[10px] text-slate-400 font-mono italic")

            # Right Side: Actions
            with ui.row().classes("items-center gap-2"):
                # Hover Actions Container
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

    def _handle_field_save(self, path: str, new_value: Any):
        """Standard save handler required by RenderingMixin."""
        if not self.db:
             return
        if self.session_id is None:
            ui.notify("No session active", type="negative")
            return

        # Generic update for any field (lists or pools)
        service = ManualEditService(self.db, self.orchestrator.tool_registry, self.orchestrator.vector_store)
        result = service.update_field(
            session_id=self.session_id,
            entity_type="character",
            entity_key=self.entity_key,
            path=path,
            new_value=new_value
        )
        if result.get("success"):
            ui.notify("Inventory updated")
            self.refresh()
        else:
            ui.notify(str(result.get("error", "Unknown error")), type="negative")

    def _remove_item(self, path: str, index: int):
        """Remove an item from a list at a specific index."""
        if not self.db or not self.session_id:
            return

        entity = get_entity(self.session_id, self.db, "character", self.entity_key)
        if not entity:
            return

        items = get_path(entity, path)
        if not isinstance(items, list) or index >= len(items):
            return

        # Remove the item
        items.pop(index)

        # Save the updated list
        self._handle_field_save(path, items)

    def _edit_item(self, path, index, current_val):
        """Open editor for a specific item in a list."""
        self._open_editor(f"Edit Item #{index+1}", f"{path}.{index}", "VAL_JSON", current_val)

    def trigger_action(self, verb: str, item_name: str):
        if not self.session_id or not self.orchestrator or not self.db or not self.db.sessions:
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
