import logging
from typing import Callable, Dict
import customtkinter as ctk
from app.gui.styles import Theme
from app.tools.builtin._state_storage import get_versions, get_entity
from .inspector_utils import display_message_state

logger = logging.getLogger(__name__)


class InventoryPanelBuilder:
    @staticmethod
    def build(
        parent: ctk.CTkFrame,
        refresh_callback: Callable,
        selection_callback: Callable,
        add_item_callback: Callable,
    ) -> dict:
        selector_frame = ctk.CTkFrame(parent)
        selector_frame.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(selector_frame, text="Owner:").pack(side="left", padx=5)
        owner_selector = ctk.CTkOptionMenu(
            selector_frame, values=["Player"], command=selection_callback
        )
        owner_selector.pack(side="left", padx=5, fill="x", expand=True)

        header_label = ctk.CTkLabel(
            parent, text="Inventory (0)", font=Theme.fonts.subheading
        )
        header_label.pack(fill="x", padx=10, pady=10)

        items_frame = ctk.CTkScrollableFrame(parent, fg_color=Theme.colors.bg_secondary)
        items_frame.pack(fill="both", expand=True, padx=5, pady=5)

        button_frame = ctk.CTkFrame(parent)
        button_frame.pack(fill="x", padx=5, pady=5)
        ctk.CTkButton(
            button_frame, text="Refresh", command=refresh_callback, height=30
        ).pack(side="left", expand=True, fill="x", padx=2)
        ctk.CTkButton(
            button_frame, text="+ Item", command=add_item_callback, height=30
        ).pack(side="left", expand=True, fill="x", padx=2)

        return {
            "owner_selector": owner_selector,
            "header_label": header_label,
            "items_frame": items_frame,
        }


class InventoryInspectorView(ctk.CTkFrame):
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.db_manager = db_manager
        self.orchestrator = None
        self.current_owner_key = "character:player"
        self.inventory_data = {}

        self.cached_versions: Dict[str, int] = {}
        self.available_keys = []

        self.widgets = InventoryPanelBuilder.build(
            self,
            refresh_callback=self.refresh,
            selection_callback=self._on_owner_selected,
            add_item_callback=self.add_item_manual,
        )

    def refresh(self):
        if not self.orchestrator or not self.orchestrator.session:
            display_message_state(
                self.widgets["items_frame"], "No session loaded.", is_error=True
            )
            return

        session_id = self.orchestrator.session.id

        # 1. Check Versions
        try:
            current_versions = get_versions(session_id, self.db_manager, "character")
        except Exception as e:
            logger.warning(f"Error fetching versions: {e}")
            return

        if not current_versions:
            self._render_empty()
            return

        # 2. Update Selector
        # Note: inventory keys are effectively character keys here
        new_keys = sorted([f"character:{k}" for k in current_versions.keys()])
        if new_keys != self.available_keys:
            display_keys = [k.split(":")[-1].title() for k in new_keys]
            self.widgets["owner_selector"].configure(values=display_keys)
            self.available_keys = new_keys
            if self.current_owner_key not in new_keys:
                self.current_owner_key = new_keys[0] if new_keys else "character:player"
                self.widgets["owner_selector"].set(
                    self.current_owner_key.split(":")[-1].title()
                )

        # 3. Check Cache
        # Strip prefix for version lookup
        char_key = self.current_owner_key.split(":")[-1]
        selected_ver = current_versions.get(char_key, 0)
        cached_ver = self.cached_versions.get(char_key, -1)

        if selected_ver > cached_ver:
            self._fetch_and_render(session_id, char_key)
            self.cached_versions[char_key] = selected_ver

    def _on_owner_selected(self, display_name: str):
        key = f"character:{display_name.lower()}"
        if key != self.current_owner_key:
            self.current_owner_key = key
            self.refresh()

    def _fetch_and_render(self, session_id, char_key):
        self.inventory_data = get_entity(
            session_id, self.db_manager, "character", char_key
        )
        self._render_inventory()

    def _render_empty(self):
        for w in self.widgets["items_frame"].winfo_children():
            w.destroy()
        display_message_state(self.widgets["items_frame"], "No inventory.")

    def _render_inventory(self):
        items_frame = self.widgets["items_frame"]
        for widget in items_frame.winfo_children():
            widget.destroy()

        if not self.inventory_data:
            return

        template_id = self.inventory_data.get("template_id")
        stat_template = (
            self.db_manager.stat_templates.get_by_id(template_id)
            if template_id
            else None
        )

        equipment = self.inventory_data.get("equipment", {})
        # Handle Dict Schema or List Schema fallback
        slots_data = equipment.get("slots", {}) if isinstance(equipment, dict) else {}
        if not slots_data:
            slots_data = self.inventory_data.get("slots", {})  # Fallback to root

        slots_def = stat_template.equipment.slots if stat_template else {}

        # Render
        total_items = 0

        # 1. Render Defined Slots
        if slots_def:
            for slot_name in slots_def.keys():
                items = slots_data.get(slot_name, [])
                self._render_slot(items_frame, slot_name, items)
                total_items += len(items)

        # 2. Render Overflow/Dynamic Slots
        for slot_name, items in slots_data.items():
            if slots_def and slot_name in slots_def:
                continue
            self._render_slot(items_frame, slot_name, items)
            total_items += len(items)

        self.widgets["header_label"].configure(text=f"Inventory ({total_items})")

    def _render_slot(self, parent, name, items):
        if not items:
            ctk.CTkLabel(
                parent, text=f"{name}: <Empty>", text_color="gray", anchor="w"
            ).pack(fill="x", padx=5)
            return
        ctk.CTkLabel(
            parent, text=f"{name}", font=Theme.fonts.subheading, anchor="w"
        ).pack(fill="x", padx=5, pady=(5, 0))
        for item in items:
            txt = f"- {item.get('name', '???')}"
            if item.get("quantity", 1) > 1:
                txt += f" (x{item['quantity']})"
            ctk.CTkLabel(parent, text=txt, anchor="w").pack(fill="x", padx=15)

    def add_item_manual(self):
        # Stub: calls self.refresh() after success
        pass
