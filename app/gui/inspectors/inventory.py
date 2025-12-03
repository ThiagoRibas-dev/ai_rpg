from nicegui import ui
from app.services.state_service import get_entity
from app.models.sheet_schema import CharacterSheetSpec


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

        # Fetch Template
        tid = entity.get("template_id")
        template = self.db.stat_templates.get_by_id(tid) if tid else None

        # We need to find where the lists are.
        # In the new Spec, they are RepeaterFields in the 'inventory' category.

        lists_to_render = []  # (key, label)

        if template and isinstance(template, CharacterSheetSpec):
            # 1. Look in Inventory Category
            if template.inventory and template.inventory.fields:
                for key, field in template.inventory.fields.items():
                    if getattr(field, "container_type", "") == "list":
                        lists_to_render.append((key, field.display.label))

        # Fallback for Legacy/Generic
        if not lists_to_render:
            # Check if entity has a raw 'inventory' dict that looks like lists
            raw_inv = entity.get("inventory", {})
            if isinstance(raw_inv, dict):
                for k in raw_inv.keys():
                    lists_to_render.append((k, k.capitalize()))
            elif isinstance(raw_inv, list):
                # Legacy flat list
                lists_to_render.append(("inventory", "Inventory"))

        # Render
        with self.container:
            for list_key, list_label in lists_to_render:
                # Extract data safely
                items = []

                # Case A: Nested in category (New Standard) -> entity['inventory']['backpack']
                if (
                    "inventory" in entity
                    and isinstance(entity["inventory"], dict)
                    and list_key in entity["inventory"]
                ):
                    items = entity["inventory"][list_key]

                # Case B: Root level (Legacy/Fallback) -> entity['backpack']
                elif list_key in entity:
                    items = entity[list_key]

                # Case C: Legacy flat inventory -> entity['inventory']
                elif list_key == "inventory" and isinstance(
                    entity.get("inventory"), list
                ):
                    items = entity.get("inventory")

                self._render_collection(list_label, items)

    def _render_collection(self, title, items):
        if not isinstance(items, list):
            return

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
                        # Left: Name & Details
                        with ui.column().classes("gap-0"):
                            name = item.get("name", "???")
                            ui.label(name).classes("font-bold text-gray-200")

                            # Render extra fields
                            extras = [
                                f"{k}: {v}"
                                for k, v in item.items()
                                if k not in ["name", "qty", "description"]
                            ]
                            if extras:
                                ui.label(", ".join(extras)).classes(
                                    "text-xs text-gray-500"
                                )

                        # Right: Quantity & Menu
                        with ui.row().classes("items-center"):
                            qty = item.get("qty", 1)
                            if qty > 1:
                                ui.badge(f"x{qty}", color="blue-900")

                            # Context Menu
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
            ui.notify("Game engine not ready", type="negative")
            return

        game_session = self.db.sessions.get_by_id(self.session_id)
        if not game_session:
            return

        command = f"I {verb} the {item_name}."
        self.orchestrator.bridge._last_input = command

        ui.notify(f"Action: {command}")

        if self.orchestrator.bridge.chat_component:
            self.orchestrator.bridge.chat_component.set_generating(True)
            self.orchestrator.bridge.chat_component.add_message("You", command, "user")

        self.orchestrator.plan_and_execute(game_session)
