# File: app/gui/panels/inspectors/character_inspector.py

import logging
from typing import Callable

import customtkinter as ctk

from app.gui.styles import Theme
from app.tools.schemas import StateQuery

from .inspector_utils import (
    create_key_value_row,
    create_track_display,
    create_vital_display,
    display_message_state,
)

logger = logging.getLogger(__name__)


class CharacterPanelBuilder:
    """Builds the static UI for the Character Inspector."""

    @staticmethod
    def build(
        parent: ctk.CTkFrame, refresh_callback: Callable, selection_callback: Callable
    ) -> dict:
        # COMMENT: The builder creates the static layout and returns widget references.
        # It takes callbacks to wire them up during construction.
        selector_frame = ctk.CTkFrame(parent)
        selector_frame.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(selector_frame, text="Character:").pack(side="left", padx=5)
        character_selector = ctk.CTkOptionMenu(
            selector_frame, values=["Player"], command=selection_callback
        )
        character_selector.pack(side="left", padx=5, fill="x", expand=True)

        scroll_frame = ctk.CTkScrollableFrame(
            parent, fg_color=Theme.colors.bg_secondary
        )
        scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

        refresh_btn = ctk.CTkButton(
            parent, text="Refresh", command=refresh_callback, height=30
        )
        refresh_btn.pack(fill="x", padx=5, pady=5)

        return {"selector": character_selector, "scroll_frame": scroll_frame}


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
            selection_callback=self._on_character_selected,
        )

    def refresh(self):
        """Query all characters and update display."""
        if not self.orchestrator or not self.orchestrator.session:
            display_message_state(
                self.widgets["scroll_frame"], "No session loaded.", is_error=True
            )
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
                self._render_character()  # Will show empty state
                return

            char_keys = list(self.all_characters.keys())
            # Pretty print keys
            display_keys = [k.title() for k in char_keys]
            self.widgets["selector"].configure(values=display_keys)

            if self.current_character_key not in char_keys:
                self.current_character_key = char_keys[0]

            self.widgets["selector"].set(self.current_character_key.title())
            self._on_character_selected(self.current_character_key.title())
        except Exception as e:
            logger.error(f"Exception in refresh: {e}", exc_info=True)
            display_message_state(
                self.widgets["scroll_frame"], f"Error: {e}", is_error=True
            )

    def _on_character_selected(self, display_name: str):
        # Simple lowercase conversion for lookup
        self.current_character_key = display_name.lower()
        self.character_data = self.all_characters.get(self.current_character_key, {})
        self._render_character()

    def _render_character(self):
        """Render character data safely."""
        scroll_frame = self.widgets["scroll_frame"]

        # Batch destroy: Unmapping first can sometimes be slightly faster visually
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

        # 1. Get Template (Safe Lookup)
        template_id = self.character_data.get("template_id")
        stat_template = None
        if template_id:
            try:
                # This DB call is usually fast (ms), but essential to keep safe
                stat_template = self.db_manager.stat_templates.get_by_id(template_id)
            except Exception as e:
                logger.error(f"Failed to load template {template_id}: {e}")

        if not stat_template:
            self._render_raw_dict(scroll_frame, self.character_data)
            return

        # 2. Render Abilities
        abilities_data = self.character_data.get("abilities", {})
        if stat_template.abilities:
            attr_frame = ctk.CTkFrame(scroll_frame)
            attr_frame.pack(fill="x", padx=10, pady=5)
            ctk.CTkLabel(
                attr_frame,
                text="Abilities",
                font=Theme.fonts.subheading,
                anchor="w",
            ).pack(fill="x", padx=10, pady=(5, 2))

            for ab_def in stat_template.abilities:
                val = abilities_data.get(ab_def.name, ab_def.default)
                # Handle Dice Codes or Integers
                val_display = str(val)
                create_key_value_row(attr_frame, ab_def.name, val_display)

        # 3. Render Vitals
        vitals_data = self.character_data.get("vitals", {})
        if stat_template.vitals:
            for vit_def in stat_template.vitals:
                data = vitals_data.get(vit_def.name, {})
                # Handle {current, max} or raw value
                if isinstance(data, dict):
                    curr = data.get("current", 0)
                    mx = data.get("max", 10)  # Default or need formula parsing
                else:
                    curr = data
                    mx = 10

                create_vital_display(scroll_frame, vit_def.name, curr, mx)

        # 4. Render Tracks
        tracks_data = self.character_data.get("tracks", {})
        if stat_template.tracks:
            for track_def in stat_template.tracks:
                val = tracks_data.get(track_def.name, 0)
                if isinstance(val, dict):
                    val = val.get("value", 0)
                create_track_display(
                    scroll_frame,
                    track_def.name,
                    val,
                    track_def.max_value,
                    track_def.visual_style,
                )

    def _render_raw_dict(self, parent, data):
        """Fallback renderer."""
        import json

        txt = ctk.CTkLabel(
            parent,
            text=json.dumps(data, indent=2),
            justify="left",
            font=Theme.fonts.monospace,
        )
        txt.pack(fill="x", padx=10)
