from nicegui import ui
from app.services.state_service import get_entity
from app.setup.setup_manifest import SetupManifest
from app.prefabs.validation import get_path


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
                self._render_collection(label, items)

    def _render_collection(self, title, items):
        with (
            ui.expansion(f"{title} ({len(items)})", icon="backpack")
            .classes("w-full bg-slate-800 rounded mb-2")
            .props("default-opened")
        ):
            if not items:
                ui.label("Empty").classes("text-gray-500 italic text-sm p-2")
                return

            with ui.column().classes("w-full gap-1 p-2"):
                for item in items:
                    with ui.row().classes(
                        "w-full justify-between items-center bg-slate-900 p-2 rounded border border-slate-700"
                    ):
                        # Name
                        name = (
                            item.get("name", "Unknown")
                            if isinstance(item, dict)
                            else str(item)
                        )
                        ui.label(name).classes("font-bold text-gray-200")

                        # Qty / Weight
                        if isinstance(item, dict):
                            extras = []
                            if item.get("qty", 1) > 1:
                                extras.append(f"x{item['qty']}")
                            if item.get("weight", 0) > 0:
                                extras.append(f"{item['weight']}lb")

                            if extras:
                                ui.label(", ".join(extras)).classes(
                                    "text-xs text-blue-400"
                                )

                        # Menu
                        with ui.button(icon="more_vert").props(
                            "flat dense round size=sm color=grey"
                        ):
                            with ui.menu():
                                ui.menu_item(
                                    "Use/Equip",
                                    on_click=lambda n=name: self.trigger_action(
                                        "use", n
                                    ),
                                )
                                ui.menu_item(
                                    "Drop",
                                    on_click=lambda n=name: self.trigger_action(
                                        "drop", n
                                    ),
                                )
                                ui.menu_item(
                                    "Inspect",
                                    on_click=lambda n=name: self.trigger_action(
                                        "inspect", n
                                    ),
                                )

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
