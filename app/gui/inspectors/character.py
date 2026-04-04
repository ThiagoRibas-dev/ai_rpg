from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from nicegui import ui

from app.models.vocabulary import PrefabID
from app.prefabs.validation import get_path
from app.services.state_service import get_entity
from app.setup.setup_manifest import SetupManifest

from .rendering_mixin import RenderingMixin

if TYPE_CHECKING:
    from app.core.orchestrator import Orchestrator
    from app.database.db_manager import DBManager

logger = logging.getLogger(__name__)


class CharacterInspector(RenderingMixin):
    """
    Universal Character Sheet Renderer.
    Adapts to SystemManifest (Lego Protocol).
    """

    def __init__(self, db_manager: DBManager, orchestrator: Orchestrator):
        self.db = db_manager
        self.orchestrator = orchestrator
        self.session_id: int | None = None
        self.container: ui.column | None = None
        self.entity_key: str = "player"

    def set_session(self, session_id: int):
        self.session_id = session_id
        if self.container:
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
        if not self.db:
            return
        entity = get_entity(self.session_id, self.db, "character", self.entity_key)
        if not entity:
            with self.container:
                 ui.label(f"Entity '{self.entity_key}' not found.").classes("text-gray-500 italic")
            return

        # 2. Fetch Manifest (Source of Truth)
        setup_data = SetupManifest(self.db).get_manifest(self.session_id)
        manifest_id = setup_data.get("manifest_id")
        manifest = None

        if manifest_id and self.db.manifests:
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
        config = field_def.config

        if prefab == PrefabID.RES_POOL:
            self._render_pool_widget(label, path, val, config)
        elif prefab == PrefabID.RES_COUNTER:
            self._render_counter_widget(label, path, val, config)
        elif prefab == PrefabID.RES_TRACK:
            self._render_track_widget(label, path, val, config)
        elif prefab.startswith("VAL_"):
            self._render_simple_val_widget(label, path, val, prefab, config)
        elif prefab in [PrefabID.CONT_LIST, PrefabID.CONT_TAGS, PrefabID.CONT_WEIGHTED]:
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
                            self._render_list_item(path, idx, item, field_def.config)


    def _render_list_item(self, path, idx, item, config=None):
        item_path = f"{path}.{idx}"

        # 3-Layer Agnostic Prefab Detection for List Items
        detected_prefab, key_map = self._detect_item_prefab(item, config)

        with ui.row().classes(
            "w-full justify-between items-center group hover:bg-slate-800 rounded px-1 transition-colors relative"
        ):
            with ui.column().classes("w-full"):
                if detected_prefab == PrefabID.RES_POOL:
                    label = self._get_item_label(item, config)
                    pool_keys = (key_map.get("curr_key"), key_map.get("max_key"))
                    self._render_pool_widget(label, item_path, item, config, mini=True, keys=pool_keys)
                elif detected_prefab == PrefabID.VAL_COMPOUND:
                    label = self._get_item_label(item, config)
                    self._render_simple_val_widget(label, item_path, item, PrefabID.VAL_COMPOUND, config, mini=True)
                elif detected_prefab == PrefabID.VAL_LADDER:
                    label = self._get_item_label(item, config)
                    self._render_simple_val_widget(label, item_path, item, PrefabID.VAL_LADDER, config, mini=True)
                elif detected_prefab == PrefabID.RES_TRACK:
                    self._render_track_widget(str(idx), item_path, item, config, mini=True)
                elif detected_prefab == PrefabID.RES_COUNTER:
                    label = self._get_item_label(item, config)
                    self._render_counter_widget(label, item_path, item, config, mini=True)
                elif detected_prefab == PrefabID.VAL_STEP_DIE:
                    self._render_simple_val_widget(str(item), item_path, item, PrefabID.VAL_STEP_DIE, config, mini=True)
                elif detected_prefab == PrefabID.VAL_BOOL:
                    self._render_simple_val_widget(str(idx), item_path, item, PrefabID.VAL_BOOL, config, mini=True)
                else:
                    # Fallback to agnostic text summary
                    txt = self._format_item_agnostic(item, config)
                    ui.label(txt).classes("text-xs text-slate-300 py-1 font-mono")

            # Hover Actions (Edit/Delete)
            with ui.row().classes("absolute right-1 top-1 opacity-0 group-hover:opacity-100 transition-opacity bg-slate-800/90 rounded px-1 gap-1 z-10"):
                ui.button(icon="edit", on_click=lambda: self._open_editor(self._get_item_label(item, config), item_path, "VAL_JSON", item)).props("flat dense round size=xs color=grey")
                ui.button(icon="delete", on_click=lambda: self._delete_list_item(path, idx)).props("flat dense round size=xs color=red")


    def _handle_field_save(self, path: str, new_value: Any):
        """Callback when a field is saved via the editor."""
        if not self.session_id:
            ui.notify("No session active", type="negative")
            return

        from app.services.manual_edit_service import ManualEditService

        if self.session_id is None:
            ui.notify("No session active", type="negative")
            return

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


    def _prompt_add_item(self, path):
        """Show dialog to add a new item/tag."""
        try:
            logger.debug(f"Prompting add item for path: {path}")
            # Use mixin's prompt which calls _handle_list_add
            super()._prompt_add_item(path)
        except Exception as e:
            logger.error(f"Error in _prompt_add_item: {e}", exc_info=True)
            ui.notify(f"Error: {e}", type="negative")

    def render(self):
        self.container = ui.column().classes("w-full p-2")
        self.refresh()
