import customtkinter as ctk
import json
import logging
import time
from app.gui.styles import Theme
from app.tools.schemas import StateQuery, StateApplyPatch, Patch

logger = logging.getLogger(__name__)

class CharacterInspectorView(ctk.CTkFrame):
    """Display character stats from game state."""
    
    def __init__(self, parent, db_manager): # Changed to db_manager
        super().__init__(parent)
        self.db_manager = db_manager # Store db_manager directly
        self.orchestrator = None # Orchestrator will be set later
        
        # Initialize missing attributes
        self.all_characters = {}
        self.current_character_key = "player"  # Default to player
        
        # ✅ FIX: Add character selector dropdown
        selector_frame = ctk.CTkFrame(self)
        selector_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(selector_frame, text="Character:").pack(side="left", padx=5)
        self.character_selector = ctk.CTkOptionMenu(
            selector_frame,
            values=["player"],
            command=self._on_character_selected
        )
        self.character_selector.pack(side="left", padx=5, fill="x", expand=True)
        
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
        """Query all characters and update display."""
        print("🔍 CharacterInspectorView.refresh() called")
        
        if not self.orchestrator:
            print("❌ No orchestrator!")
            self._show_error("No orchestrator connected")
            return
        
        if not self.orchestrator.session:
            print("❌ No session loaded!")
            self._show_error("No session loaded")
            return
        
        session_id = self.orchestrator.session.id
        print(f"✅ Session ID: {session_id}")
        
        try:
            from app.tools.registry import ToolRegistry
            registry = ToolRegistry()
            
            context = {
                "session_id": session_id,
                "db_manager": self.db_manager # Use direct db_manager
            }
            
            print(f"🔧 Querying state with context: {context}")
            
            # Query ALL characters using wildcard
            query = StateQuery(
                entity_type="character",
                key="*",
                json_path="."
            )
            result = registry.execute(query, context=context)
            
            print(f"📦 Query result: {result}")
            
            self.all_characters = result.get("value", {})
            
            print(f"👤 Found {len(self.all_characters)} characters: {list(self.all_characters.keys())}")
            
            if not self.all_characters:
                print("⚠️ No characters found, showing empty state")
                self._show_empty()
                return
            
            # ✅ FIX: Update dropdown with found characters
            char_keys = list(self.all_characters.keys())
            self.character_selector.configure(values=char_keys)
            
            # Select first character by default if current selection not in list
            if self.current_character_key not in char_keys:
                self.current_character_key = char_keys[0]
            
            print(f"📋 Selected character: {self.current_character_key}")
            
            self.character_selector.set(self.current_character_key)
            self._on_character_selected(self.current_character_key)
        
        except Exception as e:
            print(f"💥 Exception in refresh: {e}")
            import traceback
            traceback.print_exc()
            self._show_error(f"Error loading characters: {e}")
    
    def _on_character_selected(self, character_key: str):
        """Handle character selection from dropdown."""
        self.current_character_key = character_key
        self.character_data = self.all_characters.get(character_key, {})
        self._render_character()
    
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

        # Inventory
        inventory = self.character_data.get("inventory_key")
        if inventory:
            inv_label = ctk.CTkLabel(
                self.scroll_frame,
                text=f"🎒 Inventory: {inventory}",
                anchor="w"
            )
            inv_label.pack(fill="x", padx=10, pady=5)

        # Custom properties section
        properties = self.character_data.get("properties", {})
        if properties:
            prop_frame = ctk.CTkFrame(self.scroll_frame)
            prop_frame.pack(fill="x", padx=10, pady=5)

            ctk.CTkLabel(
                prop_frame,
                text="⚙️ Custom Properties",
                font=Theme.fonts.body,
                anchor="w"
            ).pack(fill="x", padx=5, pady=5)

            for key, value in properties.items():
                self._add_key_value(prop_frame, key, str(value))
        
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
    
    def __init__(self, parent, db_manager): # Changed to db_manager
        super().__init__(parent)
        self.db_manager = db_manager # Store db_manager directly
        self.orchestrator = None # Orchestrator will be set later
        
        # Initialize missing attributes
        self.all_inventories = {}
        self.current_owner_key = "inventory:player"  # Default key
        
        # ✅ FIX: Add inventory selector dropdown
        selector_frame = ctk.CTkFrame(self)
        selector_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(selector_frame, text="Owner:").pack(side="left", padx=5)
        self.owner_selector = ctk.CTkOptionMenu(
            selector_frame,
            values=["inventory:player"],
            command=self._on_owner_selected
        )
        self.owner_selector.pack(side="left", padx=5, fill="x", expand=True)
        
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
        """Query all inventories."""
        print("🔍 InventoryInspectorView.refresh() called")
        
        if not self.orchestrator:
            print("❌ No orchestrator!")
            self._show_error("No orchestrator connected")
            return
        
        if not self.orchestrator.session:
            print("❌ No session loaded!")
            self._show_error("No session loaded")
            return
        
        session_id = self.orchestrator.session.id
        print(f"✅ Session ID: {session_id}")
        
        try:
            from app.tools.registry import ToolRegistry
            registry = ToolRegistry()
            
            context = {
                "session_id": session_id,
                "db_manager": self.db_manager # Use direct db_manager
            }
            
            print(f"🔧 Querying inventories with context: {context}")
            
            # Try both "inventory" and "item" entity types
            inventories = {}
            
            for entity_type in ["inventory", "item"]:
                query = StateQuery(
                    entity_type=entity_type,
                    key="*",
                    json_path="."
                )
                result = registry.execute(query, context=context)
                
                entities = result.get("value", {})
                print(f"   Found {len(entities)} entities of type {entity_type}")
                
                if entities:
                    for key, data in entities.items():
                        inventories[f"{entity_type}:{key}"] = data
            
            self.all_inventories = inventories
            
            print(f"🎒 Total inventories: {len(self.all_inventories)}, keys: {list(self.all_inventories.keys())}")
            
            if not self.all_inventories:
                print("⚠️ No inventories found")
                self._show_empty()
                return
            
            # ✅ FIX: Update dropdown with found inventories
            inv_keys = list(self.all_inventories.keys())
            self.owner_selector.configure(values=inv_keys)
            
            if self.current_owner_key not in inv_keys:
                self.current_owner_key = inv_keys[0]
            
            print(f"📋 Selected inventory: {self.current_owner_key}")
            
            self.owner_selector.set(self.current_owner_key)
            self._on_owner_selected(self.current_owner_key)
        
        except Exception as e:
            print(f"💥 Exception in refresh: {e}")
            import traceback
            traceback.print_exc()
            self._show_error(f"Error loading inventory: {e}")
    
    def _on_owner_selected(self, owner_key: str):
        """Handle owner selection from dropdown."""
        self.current_owner_key = owner_key
        self.inventory_data = self.all_inventories.get(owner_key, {})
        self._render_inventory()
    
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
        
        if not self.orchestrator or not self.orchestrator.session:
            self._show_error("No active session")
            return
        
        session_id = self.orchestrator.session.id
        
        try:
            from app.tools.registry import ToolRegistry
            registry = ToolRegistry()
            
            # Generate a simple ID
            item_id = f"item_{int(time.time())}"
            
            # Add to inventory state
            patch_call = StateApplyPatch(
                entity_type="inventory",
                key="player",
                patch=[
                    Patch(
                        op="add",
                        path="/items/-",
                        value={
                            "id": item_id,
                            "name": item_name,
                            "quantity": 1,
                            "equipped": False
                        }
                    )
                ]
            )
            registry.execute(patch_call, context={"session_id": session_id, "db_manager": self.db_manager})
            
            self.refresh()
        
        except Exception as e:
            logger.error(f"Error adding item: {e}", exc_info=True)
            self._show_error(f"Error adding item: {e}")
    
    def _show_empty(self):
        """Show empty state."""
        for widget in self.items_frame.winfo_children():
            widget.destroy()
        
        ctk.CTkLabel(
            self.items_frame,
            text="No inventory data.\n\nThe AI will track items as you play.",
            text_color=Theme.colors.text_muted
        ).pack(expand=True, pady=50)

    def _show_error(self, message):
        """Show error message."""
        for widget in self.items_frame.winfo_children():
            widget.destroy()
        
        label = ctk.CTkLabel(
            self.items_frame,
            text=message,
            text_color=Theme.colors.text_muted,
            font=Theme.fonts.body,
            wraplength=400
        )
        label.pack(expand=True, pady=50)


class QuestInspectorView(ctk.CTkFrame):
    """Display active quests."""
    
    def __init__(self, parent, db_manager): # Changed to db_manager
        super().__init__(parent)
        self.db_manager = db_manager # Store db_manager directly
        self.orchestrator = None # Orchestrator will be set later
        
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
        """Query all quests."""
        print("🔍 QuestInspectorView.refresh() called")
        
        if not self.orchestrator:
            print("❌ No orchestrator!")
            self._show_error("No orchestrator connected")
            return
        
        if not self.orchestrator.session:
            print("❌ No session loaded!")
            self._show_error("No session loaded")
            return
        
        session_id = self.orchestrator.session.id
        print(f"✅ Session ID: {session_id}")
        
        try:
            from app.tools.registry import ToolRegistry
            registry = ToolRegistry()
            
            context = {
                "session_id": session_id,
                "db_manager": self.db_manager # Use direct db_manager
            }
            
            print(f"🔧 Querying quests with context: {context}")
            
            # Query all quests using wildcard
            query = StateQuery(
                entity_type="quest",
                key="*",
                json_path="."
            )
            result = registry.execute(query, context=context)
            
            print(f"📦 Query result: {result}")
            
            self.quests_data = result.get("value", {})
            
            print(f"📜 Found {len(self.quests_data)} quests: {list(self.quests_data.keys())}")
            
            self._render_quests()
        
        except Exception as e:
            print(f"💥 Exception in refresh: {e}")
            import traceback
            traceback.print_exc()
            self._show_error(f"Error loading quests: {e}")
    
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
