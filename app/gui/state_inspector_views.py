import customtkinter as ctk
import json
from app.gui.styles import Theme

class CharacterInspectorView(ctk.CTkFrame):
    """Display character stats from game state."""
    
    def __init__(self, parent, orchestrator):
        super().__init__(parent)
        self.orchestrator = orchestrator
        
        # Scrollable content
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color=Theme.colors.bg_secondary)
        self.scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Refresh button
        refresh_btn = ctk.CTkButton(
            self,
            text="🔄 Refresh",
            command=self.refresh,
            height=30
        )
        refresh_btn.pack(fill="x", padx=5, pady=5)
        
        self.character_data = {}
    
    def refresh(self):
        """Query state and update display."""
        if not self.orchestrator or not self.orchestrator.session:
            return
        
        try:
            from app.tools.registry import ToolRegistry
            registry = ToolRegistry()
            
            # ✅ Pass proper context
            context = {
                "session_id": self.orchestrator.session.id if self.orchestrator.session else None,
                "db_manager": self.orchestrator.db_manager
            }
            
            result = registry.execute_tool(
                "state.query",
                {"entity_type": "character", "key": "player", "json_path": "."},
                context=context
            )
            
            self.character_data = result.get("value", {})
            self._render_character()

        except Exception:
            self._show_error("No character data found.\n\nThe AI hasn't created a character yet.\nStart playing to generate state!")
    
    def _render_character(self):
        """Render character data as a card."""
        # Clear existing widgets
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        
        if not self.character_data:
            self._show_empty()
            return
        
        # Character name header
        name = self.character_data.get("name", "Unknown")
        race = self.character_data.get("race", "")
        char_class = self.character_data.get("class", "")
        level = self.character_data.get("level", 1)
        
        header = ctk.CTkLabel(
            self.scroll_frame,
            text=f"{name} - {race} {char_class} (Level {level})",
            font=Theme.fonts.subheading,
            anchor="w"
        )
        header.pack(fill="x", padx=10, pady=(10, 5))
        
        # Attributes section
        attributes = self.character_data.get("attributes", {})
        if attributes:
            attr_frame = ctk.CTkFrame(self.scroll_frame)
            attr_frame.pack(fill="x", padx=10, pady=5)
            
            ctk.CTkLabel(
                attr_frame,
                text="⚔️ Attributes",
                font=Theme.fonts.body,
                anchor="w"
            ).pack(fill="x", padx=5, pady=5)
            
            for key, value in attributes.items():
                self._add_key_value(attr_frame, key.replace("_", " ").title(), str(value))
        
        # Conditions section
        conditions = self.character_data.get("conditions", [])
        if conditions:
            cond_frame = ctk.CTkFrame(self.scroll_frame)
            cond_frame.pack(fill="x", padx=10, pady=5)
            
            ctk.CTkLabel(
                cond_frame,
                text="🩹 Conditions",
                font=Theme.fonts.body,
                anchor="w"
            ).pack(fill="x", padx=5, pady=5)
            
            for condition in conditions:
                ctk.CTkLabel(
                    cond_frame,
                    text=f"  • {condition}",
                    anchor="w",
                    text_color=Theme.colors.tool_error
                ).pack(fill="x", padx=10)
        
        # Location
        location = self.character_data.get("location")
        if location:
            loc_label = ctk.CTkLabel(
                self.scroll_frame,
                text=f"📍 Location: {location}",
                anchor="w"
            )
            loc_label.pack(fill="x", padx=10, pady=5)
        
        # Raw JSON view (collapsible)
        json_btn = ctk.CTkButton(
            self.scroll_frame,
            text="View Raw JSON",
            command=self._toggle_json,
            height=30
        )
        json_btn.pack(fill="x", padx=10, pady=10)
    
    def _add_key_value(self, parent, key, value):
        """Add a key-value pair display."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=2)
        
        ctk.CTkLabel(row, text=f"{key}:", anchor="w", width=150).pack(side="left")
        ctk.CTkLabel(row, text=value, anchor="w", text_color=Theme.colors.text_secondary).pack(side="left")
    
    def _show_empty(self):
        """Show empty state message."""
        label = ctk.CTkLabel(
            self.scroll_frame,
            text="No character data available.\n\nThe AI will create character state as you play.",
            text_color=Theme.colors.text_muted,
            font=Theme.fonts.body
        )
        label.pack(expand=True, pady=50)
    
    def _show_error(self, message):
        """Show error message."""
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        
        label = ctk.CTkLabel(
            self.scroll_frame,
            text=message,
            text_color=Theme.colors.text_muted,
            font=Theme.fonts.body,
            wraplength=400
        )
        label.pack(expand=True, pady=50)
    
    def _toggle_json(self):
        """Show/hide raw JSON."""
        # Implementation: create a popup with JSON viewer
        dialog = ctk.CTkToplevel(self)
        dialog.title("Raw Character Data")
        dialog.geometry("600x400")
        
        textbox = ctk.CTkTextbox(dialog)
        textbox.pack(fill="both", expand=True, padx=10, pady=10)
        
        json_str = json.dumps(self.character_data, indent=2)
        textbox.insert("1.0", json_str)
        textbox.configure(state="disabled")


class InventoryInspectorView(ctk.CTkFrame):
    """Display and interact with inventory."""
    
    def __init__(self, parent, orchestrator):
        super().__init__(parent)
        self.orchestrator = orchestrator
        
        # Header with capacity
        self.header_label = ctk.CTkLabel(
            self,
            text="🎒 Inventory (0/10)",
            font=Theme.fonts.subheading
        )
        self.header_label.pack(fill="x", padx=10, pady=10)
        
        # Items list
        self.items_frame = ctk.CTkScrollableFrame(self, fg_color=Theme.colors.bg_secondary)
        self.items_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Currency display
        self.currency_frame = ctk.CTkFrame(self)
        self.currency_frame.pack(fill="x", padx=5, pady=5)
        
        # Action buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkButton(
            button_frame,
            text="🔄 Refresh",
            command=self.refresh,
            height=30
        ).pack(side="left", expand=True, fill="x", padx=2)
        
        ctk.CTkButton(
            button_frame,
            text="➕ Add Item (Manual)",
            command=self.add_item_manual,
            height=30
        ).pack(side="left", expand=True, fill="x", padx=2)
        
        self.inventory_data = {}
    
    def refresh(self):
        """Query inventory state."""
        if not self.orchestrator or not self.orchestrator.session:
            return
        
        try:
            from app.tools.registry import ToolRegistry
            registry = ToolRegistry()
            
            # ✅ Pass proper context
            context = {
                "session_id": self.orchestrator.session.id if self.orchestrator.session else None,
                "db_manager": self.orchestrator.db_manager
            }
            
            result = registry.execute_tool(
                "state.query",
                {"entity_type": "inventory", "key": "player", "json_path": "."},
                context=context
            )
            
            self.inventory_data = result.get("value", {})
            self._render_inventory()
        
        except Exception:
            self._show_empty()
    
    def _render_inventory(self):
        """Render inventory items."""
        # Clear items
        for widget in self.items_frame.winfo_children():
            widget.destroy()
        
        for widget in self.currency_frame.winfo_children():
            widget.destroy()
        
        if not self.inventory_data:
            self._show_empty()
            return
        
        # Update header with capacity
        slots_used = self.inventory_data.get("slots_used", 0)
        slots_max = self.inventory_data.get("slots_max", 10)
        self.header_label.configure(text=f"🎒 Inventory ({slots_used}/{slots_max})")
        
        # Render items
        items = self.inventory_data.get("items", [])
        for item in items:
            self._create_item_card(item)
        
        if not items:
            ctk.CTkLabel(
                self.items_frame,
                text="No items",
                text_color=Theme.colors.text_muted
            ).pack(pady=20)
        
        # Render currency
        currency = self.inventory_data.get("currency", {})
        if currency:
            currency_text = " | ".join([f"{v} {k}" for k, v in currency.items()])
            ctk.CTkLabel(
                self.currency_frame,
                text=f"💰 {currency_text}",
                font=Theme.fonts.body
            ).pack(padx=10, pady=5)
    
    def _create_item_card(self, item):
        """Create a card for a single item."""
        card = ctk.CTkFrame(self.items_frame, border_width=1)
        card.pack(fill="x", padx=5, pady=3)
        
        # Item header
        header_frame = ctk.CTkFrame(card, fg_color="transparent")
        header_frame.pack(fill="x", padx=5, pady=5)
        
        name = item.get("name", "Unknown Item")
        quantity = item.get("quantity", 1)
        equipped = item.get("equipped", False)
        
        name_text = f"{'⚔️' if equipped else '📦'} {name}"
        if quantity > 1:
            name_text += f" x{quantity}"
        
        ctk.CTkLabel(
            header_frame,
            text=name_text,
            font=Theme.fonts.body,
            anchor="w"
        ).pack(side="left", fill="x", expand=True)
        
        # Action: Drop item (via AI)
        ctk.CTkButton(
            header_frame,
            text="🗑️",
            width=30,
            height=24,
            command=lambda i=item: self.drop_item(i),
            fg_color=Theme.colors.button_danger,
            hover_color=Theme.colors.button_danger_hover
        ).pack(side="right")
    
    def drop_item(self, item):
        """Drop an item by suggesting it to the user input."""
        item_name = item.get("name", "item")
        
        # Pre-fill the user input with a drop command
        if hasattr(self.orchestrator, 'view'):
            self.orchestrator.view.user_input.delete("1.0", "end")
            self.orchestrator.view.user_input.insert("1.0", f"I drop the {item_name}.")
    
    def add_item_manual(self):
        """Manually add an item (for testing or DM intervention)."""
        dialog = ctk.CTkInputDialog(text="Enter item name:", title="Add Item")
        item_name = dialog.get_input()
        
        if not item_name:
            return
        
        try:
            from app.tools.registry import ToolRegistry
            registry = ToolRegistry()
            
            # Generate a simple ID
            import time
            item_id = f"item_{int(time.time())}"
            
            # Add to inventory state
            registry.execute_tool(
                "state.apply_patch",
                {
                    "entity_type": "inventory",
                    "key": "player",
                    "patch": [
                        {
                            "op": "add",
                            "path": "/items/-",
                            "value": {
                                "id": item_id,
                                "name": item_name,
                                "quantity": 1,
                                "equipped": False
                            }
                        }
                    ]
                },
                context={}
            )
            
            self.refresh()
        
        except Exception as e:
            print(f"Error adding item: {e}")
    
    def _show_empty(self):
        """Show empty state."""
        for widget in self.items_frame.winfo_children():
            widget.destroy()
        
        ctk.CTkLabel(
            self.items_frame,
            text="No inventory data.\n\nThe AI will track items as you play.",
            text_color=Theme.colors.text_muted
        ).pack(expand=True, pady=50)


class QuestInspectorView(ctk.CTkFrame):
    """Display active quests."""
    
    def __init__(self, parent, orchestrator):
        super().__init__(parent)
        self.orchestrator = orchestrator
        
        # Scrollable quest list
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color=Theme.colors.bg_secondary)
        self.scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Refresh button
        ctk.CTkButton(
            self,
            text="🔄 Refresh",
            command=self.refresh,
            height=30
        ).pack(fill="x", padx=5, pady=5)
        
        self.quests_data = {}
    
    def refresh(self):
        """Query quest state."""
        if not self.orchestrator or not self.orchestrator.session:
            return
        
        try:
            from app.tools.registry import ToolRegistry
            registry = ToolRegistry()
            
            # ✅ Pass proper context
            context = {
                "session_id": self.orchestrator.session.id if self.orchestrator.session else None,
                "db_manager": self.orchestrator.db_manager
            }
            
            # Quests are stored as multiple entities (quest_001, quest_002, etc.)
            # For now, we'll try to query a "quests" collection at root
            result = registry.execute_tool(
                "state.query",
                {"entity_type": "quests", "key": "*", "json_path": "."},  # ✅ Use wildcard
                context=context
            )
            
            self.quests_data = result.get("value", {})
            self._render_quests()
        
        except Exception:
            self._show_empty()
    
    def _render_quests(self):
        """Render quest cards."""
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        
        if not self.quests_data or not isinstance(self.quests_data, dict):
            self._show_empty()
            return
        
        for quest_id, quest in self.quests_data.items():
            self._create_quest_card(quest_id, quest)
    
    def _create_quest_card(self, quest_id, quest):
        """Create a card for a single quest."""
        card = ctk.CTkFrame(self.scroll_frame, border_width=2)
        card.pack(fill="x", padx=5, pady=5)
        
        # Quest header
        title = quest.get("title", "Unknown Quest")
        quest_type = quest.get("type", "side")
        status = quest.get("status", "active")
        
        icon = "⭐" if quest_type == "main" else "📜"
        status_color = Theme.colors.text_tool_success if status == "completed" else Theme.colors.text_secondary
        
        header = ctk.CTkLabel(
            card,
            text=f"{icon} {title} [{status.upper()}]",
            font=Theme.fonts.subheading,
            anchor="w",
            text_color=status_color
        )
        header.pack(fill="x", padx=10, pady=(10, 5))
        
        # Progress
        progress = quest.get("progress")
        if progress:
            ctk.CTkLabel(
                card,
                text=f"Progress: {progress}",
                anchor="w",
                font=Theme.fonts.body_small
            ).pack(fill="x", padx=10, pady=2)
        
        # Objectives
        objectives = quest.get("objectives", [])
        if objectives:
            obj_frame = ctk.CTkFrame(card, fg_color="transparent")
            obj_frame.pack(fill="x", padx=10, pady=5)
            
            for obj in objectives:
                completed = obj.get("completed", False)
                text = obj.get("text", "")
                checkbox = "✅" if completed else "⬜"
                
                ctk.CTkLabel(
                    obj_frame,
                    text=f"{checkbox} {text}",
                    anchor="w",
                    font=Theme.fonts.body_small
                ).pack(fill="x", padx=5, pady=1)
    
    def _show_empty(self):
        """Show empty state."""
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        
        ctk.CTkLabel(
            self.scroll_frame,
            text="No active quests.\n\nQuests will appear as the story progresses.",
            text_color=Theme.colors.text_muted
        ).pack(expand=True, pady=50)
