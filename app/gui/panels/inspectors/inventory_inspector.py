# File: app/gui/panels/inspectors/inventory_inspector.py

import logging
from typing import Callable

import customtkinter as ctk

from app.gui.styles import Theme
from app.tools.schemas import InventoryAddItem, StateQuery

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
            selector_frame, values=["Player"], command=selection_callback
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
            # Just get characters for now, assuming inventory is embedded in Character via Slots
            for entity_type in ["character"]: # simplified
                query = StateQuery(entity_type=entity_type, key="*", json_path=".")
                result = registry.execute(query, context=context)
                entities = result.get("value", {})
                if entities:
                    for key, data in entities.items():
                        # Map character to an inventory view key
                        inventories[f"character:{key}"] = data
            
            self.all_inventories = inventories

            if not self.all_inventories:
                self._render_inventory() # Will show empty state
                return

            # Format keys for display (remove 'character:' prefix and Title Case)
            # Store a map of Display Name -> Real Key if needed, but for now we assume uniqueness
            inv_keys = list(self.all_inventories.keys())
            display_keys = [k.split(":")[-1].title() for k in inv_keys]
            self.widgets["owner_selector"].configure(values=display_keys)
            
            if self.current_owner_key not in inv_keys:
                self.current_owner_key = inv_keys[0]
            self.widgets["owner_selector"].set(self.current_owner_key.split(":")[-1].title())
            self._on_owner_selected(self.current_owner_key.split(":")[-1].title())
        except Exception as e:
            logger.error(f"Exception in refresh: {e}", exc_info=True)
            display_message_state(self.widgets["items_frame"], f"Error: {e}", is_error=True)

    def _on_owner_selected(self, display_name: str):
        # Convert display name back to key (simplistic assumption: lowercase)
        # In a robust system, use a lookup dict.
        key_guess = f"character:{display_name.lower()}"
        
        # Try to find the exact key in our data
        if key_guess in self.all_inventories:
             self.current_owner_key = key_guess
        else:
             # Fallback to first available if guess fails
             pass 
             
        self.inventory_data = self.all_inventories.get(self.current_owner_key, {})
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
            
        # Check for Template
        template_id = self.inventory_data.get("template_id")
        stat_template = None
        if template_id:
             stat_template = self.db_manager.stat_templates.get_by_id(template_id)

        # Render by Slot
        slots_data = self.inventory_data.get("slots", {})
        
        # If no template, try to dump what's in 'slots' generically
        slots_to_render = stat_template.slots if stat_template else []
        
        if not slots_to_render and slots_data:
             # Fallback: iterate keys
             for k in slots_data.keys():
                 self._render_single_slot(items_frame, k, slots_data[k])
        
        total_items = 0
        for slot_def in slots_to_render:
            items = slots_data.get(slot_def.name, [])
            self._render_single_slot(items_frame, slot_def.name, items, slot_def.fixed_capacity)
            total_items += len(items)

        self.widgets["header_label"].configure(text=f"🎒 Inventory ({total_items} items)")

    def _render_single_slot(self, parent, name, items, capacity=None):
        cap_str = f" (Max {capacity})" if capacity else ""
        
        if not items:
            # Compact Empty Display
            ctk.CTkLabel(parent, text=f"{name}: <Empty>", text_color="gray", anchor="w").pack(fill="x", padx=5, pady=2)
            return

        # Normal Display
        ctk.CTkLabel(parent, text=f"{name}{cap_str}", font=Theme.fonts.subheading, anchor="w").pack(fill="x", padx=5, pady=(10,2))
            
        for item in items:
            qty = item.get("quantity", 1)
            txt = f"- {item.get('name', '???')}"
            if qty > 1:
                txt += f" (x{qty})"
            ctk.CTkLabel(parent, text=txt, anchor="w").pack(fill="x", padx=15)

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
            
            # CHANGE 2: Use the specific InventoryAddItem tool instead of generic Patch
            # Extract the actual key from "character:player" -> "player"
            owner_key_stripped = self.current_owner_key.split(":")[-1] if ":" in self.current_owner_key else self.current_owner_key
            
            tool_call = InventoryAddItem(
                owner_key=owner_key_stripped,
                item_name=item_name,
                quantity=1
            )
            
            registry.execute(tool_call, context={"session_id": session_id, "db_manager": self.db_manager})
            self.refresh()
        except Exception as e:
            logger.error(f"Error adding item: {e}", exc_info=True)
            display_message_state(self.widgets["items_frame"], f"Error adding item: {e}", is_error=True)
