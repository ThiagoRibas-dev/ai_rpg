# File: app/gui/panels/inspectors/character_inspector.py
# --- NEW FILE ---

import customtkinter as ctk
import logging
from typing import Callable
from app.gui.styles import Theme
from app.tools.schemas import StateQuery
from .inspector_utils import create_key_value_row, display_message_state

logger = logging.getLogger(__name__)

class CharacterPanelBuilder:
    """Builds the static UI for the Character Inspector."""
    @staticmethod
    def build(parent: ctk.CTkFrame, refresh_callback: Callable, selection_callback: Callable) -> dict:
        # COMMENT: The builder creates the static layout and returns widget references.
        # It takes callbacks to wire them up during construction.
        selector_frame = ctk.CTkFrame(parent)
        selector_frame.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(selector_frame, text="Character:").pack(side="left", padx=5)
        character_selector = ctk.CTkOptionMenu(
            selector_frame, values=["player"], command=selection_callback
        )
        character_selector.pack(side="left", padx=5, fill="x", expand=True)

        scroll_frame = ctk.CTkScrollableFrame(parent, fg_color=Theme.colors.bg_secondary)
        scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

        refresh_btn = ctk.CTkButton(parent, text="Refresh", command=refresh_callback, height=30)
        refresh_btn.pack(fill="x", padx=5, pady=5)

        return {
            "selector": character_selector,
            "scroll_frame": scroll_frame
        }

class CharacterInspectorView(ctk.CTkFrame):
    """Display character stats from game state."""

    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.db_manager = db_manager
        self.orchestrator = None
        self.all_characters = {}
        self.current_character_key = "player"
        self.character_data = {}

        # COMMENT: UI construction is now delegated to the builder.
        self.widgets = CharacterPanelBuilder.build(
            self,
            refresh_callback=self.refresh,
            selection_callback=self._on_character_selected
        )

    def refresh(self):
        """Query all characters and update display."""
        if not self.orchestrator or not self.orchestrator.session:
            display_message_state(self.widgets["scroll_frame"], "No session loaded.", is_error=True)
            return

        session_id = self.orchestrator.session.id
        try:
            from app.tools.registry import ToolRegistry
            registry = ToolRegistry()
            context = {"session_id": session_id, "db_manager": self.db_manager}
            query = StateQuery(entity_type="character", key="*", json_path=".")
            result = registry.execute(query, context=context)
            self.all_characters = result.get("value", {})

            if not self.all_characters:
                self._render_character() # Will show empty state
                return

            char_keys = list(self.all_characters.keys())
            self.widgets["selector"].configure(values=char_keys)
            if self.current_character_key not in char_keys:
                self.current_character_key = char_keys[0]

            self.widgets["selector"].set(self.current_character_key)
            self._on_character_selected(self.current_character_key)
        except Exception as e:
            logger.error(f"Exception in refresh: {e}", exc_info=True)
            display_message_state(self.widgets["scroll_frame"], f"Error: {e}", is_error=True)

    def _on_character_selected(self, character_key: str):
        self.current_character_key = character_key
        self.character_data = self.all_characters.get(character_key, {})
        self._render_character()

    def _render_character(self):
        """Render character data. This method is now much cleaner."""
        # COMMENT: The rendering logic no longer creates complex widgets, it just
        # configures them or calls simple utility functions.
        scroll_frame = self.widgets["scroll_frame"]
        for widget in scroll_frame.winfo_children():
            widget.destroy()

        if not self.character_data:
            display_message_state(scroll_frame, "No character data available.")
            return

        name = self.character_data.get("name", "Unknown")
        
        header_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(5, 10))
        ctk.CTkLabel(
            header_frame,
            text=name,
            font=Theme.fonts.heading,
            anchor="w",
        ).pack(side="left")
        
        attributes = self.character_data.get("attributes", {})
        if attributes:
            attr_frame = ctk.CTkFrame(scroll_frame)
            attr_frame.pack(fill="x", padx=10, pady=5)
            ctk.CTkLabel(
                attr_frame,
                text="Attributes",
                font=Theme.fonts.subheading,
                anchor="w",
            ).pack(fill="x", padx=10, pady=(5, 2))
            for key, value in attributes.items():
                # COMMENT: Using the new utility function for clean, consistent rows.
                create_key_value_row(attr_frame, key.replace("_", " ").title(), str(value))
