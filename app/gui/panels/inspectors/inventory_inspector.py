# File: app/gui/panels/inspectors/inventory_inspector.py
# --- NEW FILE ---

import customtkinter as ctk
import logging
import time
from typing import Callable
from app.gui.styles import Theme
from app.tools.schemas import StateQuery, StateApplyPatch, Patch
from .inspector_utils import display_message_state

logger = logging.getLogger(__name__)

class InventoryPanelBuilder:
    """Builds the static UI for the Inventory Inspector."""
    @staticmethod
    def build(parent: ctk.CTkFrame, refresh_callback: Callable, selection_callback: Callable, add_item_callback: Callable) -> dict:
        selector_frame = ctk.CTkFrame(parent)
        selector_frame.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(selector_frame, text="Owner:").pack(side="left", padx=5)
        owner_selector = ctk.CTkOptionMenu(
            selector_frame, values=["inventory:player"], command=selection_callback
        )
        owner_selector.pack(side="left", padx=5, fill="x", expand=True)

        header_label = ctk.CTkLabel(
            parent, text="🎒 Inventory (0/0)", font=Theme.fonts.subheading
        )
        header_label.pack(fill="x", padx=10, pady=10)

        items_frame = ctk.CTkScrollableFrame(
            parent, fg_color=Theme.colors.bg_secondary
        )
        items_frame.pack(fill="both", expand=True, padx=5, pady=5)

        currency_frame = ctk.CTkFrame(parent)
        currency_frame.pack(fill="x", padx=5, pady=5)

        button_frame = ctk.CTkFrame(parent)
        button_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkButton(
            button_frame, text="🔄 Refresh", command=refresh_callback, height=30
        ).pack(side="left", expand=True, fill="x", padx=2)

        ctk.CTkButton(
            button_frame,
            text="➕ Add Item (Manual)",
            command=add_item_callback,
            height=30,
        ).pack(side="left", expand=True, fill="x", padx=2)

        return {
            "owner_selector": owner_selector,
            "header_label": header_label,
            "items_frame": items_frame,
            "currency_frame": currency_frame,
        }

class InventoryInspectorView(ctk.CTkFrame):
    """Display and interact with inventory."""

    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.db_manager = db_manager
        self.orchestrator = None
        self.all_inventories = {}
        self.current_owner_key = "inventory:player"
        self.inventory_data = {}

        self.widgets = InventoryPanelBuilder.build(
            self,
            refresh_callback=self.refresh,
            selection_callback=self._on_owner_selected,
            add_item_callback=self.add_item_manual
        )

    def refresh(self):
        """Query all inventories."""
        if not self.orchestrator or not self.orchestrator.session:
            display_message_state(self.widgets["items_frame"], "No session loaded.", is_error=True)
            return

        session_id = self.orchestrator.session.id
        try:
            from app.tools.registry import ToolRegistry
            registry = ToolRegistry()
            context = {"session_id": session_id, "db_manager": self.db_manager}

            inventories = {}
            for entity_type in ["inventory", "item"]:
                query = StateQuery(entity_type=entity_type, key="*", json_path=".")
                result = registry.execute(query, context=context)
                entities = result.get("value", {})
                if entities:
                    for key, data in entities.items():
                        inventories[f"{entity_type}:{key}"] = data
            
            self.all_inventories = inventories

            if not self.all_inventories:
                self._render_inventory() # Will show empty state
                return

            inv_keys = list(self.all_inventories.keys())
            self.widgets["owner_selector"].configure(values=inv_keys)
            if self.current_owner_key not in inv_keys:
                self.current_owner_key = inv_keys[0]

            self.widgets["owner_selector"].set(self.current_owner_key)
            self._on_owner_selected(self.current_owner_key)
        except Exception as e:
            logger.error(f"Exception in refresh: {e}", exc_info=True)
            display_message_state(self.widgets["items_frame"], f"Error: {e}", is_error=True)

    def _on_owner_selected(self, owner_key: str):
        self.current_owner_key = owner_key
        self.inventory_data = self.all_inventories.get(owner_key, {})
        self._render_inventory()

    def _render_inventory(self):
        items_frame = self.widgets["items_frame"]
        for widget in items_frame.winfo_children():
            widget.destroy()

        currency_frame = self.widgets["currency_frame"]
        for widget in currency_frame.winfo_children():
            widget.destroy()

        if not self.inventory_data:
            display_message_state(items_frame, "No inventory data available.")
            self.widgets["header_label"].configure(text="🎒 Inventory (0/0)")
            return

        slots_used = self.inventory_data.get("slots_used", 0)
        slots_max = self.inventory_data.get("slots_max", 10)
        self.widgets["header_label"].configure(text=f"🎒 Inventory ({slots_used}/{slots_max})")

        items = self.inventory_data.get("items", [])
        if not items:
            ctk.CTkLabel(items_frame, text="No items", text_color=Theme.colors.text_muted).pack(pady=20)

        for item in items:
            # create_item_card(items_frame, item, self.drop_item) # Temporarily commented out
            pass # Placeholder for future item card creation

        currency = self.inventory_data.get("currency", {})
        if currency:
            currency_text = " | ".join([f"{v} {k}" for k, v in currency.items()])
            ctk.CTkLabel(currency_frame, text=f"💰 {currency_text}", font=Theme.fonts.body).pack(padx=10, pady=5)

    def drop_item(self, item):
        item_name = item.get("name", "item")
        if hasattr(self.orchestrator, "view"):
            self.orchestrator.view.user_input.delete("1.0", "end")
            self.orchestrator.view.user_input.insert("1.0", f"I drop the {item_name}.")

    def add_item_manual(self):
        dialog = ctk.CTkInputDialog(text="Enter item name:", title="Add Item")
        item_name = dialog.get_input()

        if not item_name:
            return

        if not self.orchestrator or not self.orchestrator.session:
            display_message_state(self.widgets["items_frame"], "No active session", is_error=True)
            return

        session_id = self.orchestrator.session.id
        try:
            from app.tools.registry import ToolRegistry
            registry = ToolRegistry()
            item_id = f"item_{int(time.time())}"
            patch_call = StateApplyPatch(
                entity_type="inventory",
                key="player",
                patch=[
                    Patch(
                        op="add",
                        path="/items/-",
                        value={"id": item_id, "name": item_name, "quantity": 1, "equipped": False},
                    )
                ],
            )
            registry.execute(patch_call, context={"session_id": session_id, "db_manager": self.db_manager})
            self.refresh()
        except Exception as e:
            logger.error(f"Error adding item: {e}", exc_info=True)
            display_message_state(self.widgets["items_frame"], f"Error adding item: {e}", is_error=True)
