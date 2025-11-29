import logging
from typing import Callable, Dict
import customtkinter as ctk
from app.gui.styles import Theme
from app.tools.builtin._state_storage import get_versions, get_entity
from .inspector_utils import (
    create_key_value_row,
    create_track_display,
    create_vital_display,
    display_message_state,
)

logger = logging.getLogger(__name__)


class CharacterPanelBuilder:
    @staticmethod
    def build(
        parent: ctk.CTkFrame, refresh_callback: Callable, selection_callback: Callable
    ) -> dict:
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
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.db_manager = db_manager
        self.orchestrator = None
        self.current_character_key = "player"
        self.character_data = {}

        # Cache Tracking: { "player": 5, "goblin": 1 }
        self.cached_versions: Dict[str, int] = {}
        # Track available keys to know when to update selector
        self.available_keys = []

        self.widgets = CharacterPanelBuilder.build(
            self,
            refresh_callback=self.refresh,
            selection_callback=self._on_character_selected,
        )

    def refresh(self):
        if not self.orchestrator or not self.orchestrator.session:
            display_message_state(
                self.widgets["scroll_frame"], "No session loaded.", is_error=True
            )
            return

        session_id = self.orchestrator.session.id

        # 1. Lightweight Query: Get Versions
        try:
            current_versions = get_versions(session_id, self.db_manager, "character")
        except Exception as e:
            logger.error(f"Failed to fetch versions: {e}")
            return

        if not current_versions:
            self._render_empty()
            return

        # 2. Update Selector (if keys changed)
        new_keys = sorted(list(current_versions.keys()))
        if new_keys != self.available_keys:
            display_keys = [k.title() for k in new_keys]
            self.widgets["selector"].configure(values=display_keys)
            self.available_keys = new_keys

            # Ensure selection is valid
            if self.current_character_key not in new_keys:
                self.current_character_key = new_keys[0] if new_keys else "player"
                self.widgets["selector"].set(self.current_character_key.title())

        # 3. Check specific cache for CURRENTLY selected character
        # We only re-render if the selected character's version has changed
        selected_ver = current_versions.get(self.current_character_key, 0)
        cached_ver = self.cached_versions.get(self.current_character_key, -1)

        if selected_ver > cached_ver:
            logger.debug(
                f"Cache miss for {self.current_character_key} (DB:{selected_ver} > Cache:{cached_ver}). Rendering."
            )
            self._fetch_and_render(session_id)
            self.cached_versions[self.current_character_key] = selected_ver
        else:
            logger.debug(
                f"Cache hit for {self.current_character_key}. Skipping render."
            )

    def _on_character_selected(self, display_name: str):
        key = display_name.lower()
        if key != self.current_character_key:
            self.current_character_key = key
            # Force render on switch (or check cache)
            self.refresh()

    def _fetch_and_render(self, session_id):
        self.character_data = get_entity(
            session_id, self.db_manager, "character", self.current_character_key
        )
        self._render_character()

    def _render_empty(self):
        for widget in self.widgets["scroll_frame"].winfo_children():
            widget.destroy()
        display_message_state(self.widgets["scroll_frame"], "No characters found.")

    def _render_character(self):
        scroll_frame = self.widgets["scroll_frame"]
        for widget in scroll_frame.winfo_children():
            widget.destroy()

        if not self.character_data:
            display_message_state(scroll_frame, "No data.")
            return

        name = self.character_data.get("name", "Unknown")
        ctk.CTkLabel(
            scroll_frame, text=name, font=Theme.fonts.heading, anchor="w"
        ).pack(fill="x", padx=10, pady=(5, 10))

        # Template
        template_id = self.character_data.get("template_id")
        stat_template = (
            self.db_manager.stat_templates.get_by_id(template_id)
            if template_id
            else None
        )

        if not stat_template:
            self._render_raw_dict(scroll_frame, self.character_data)
            return

        # Abilities
        abilities_data = self.character_data.get(
            "fundamental_stats", {}
        )  # New Schema Key
        if not abilities_data:
            abilities_data = self.character_data.get("abilities", {})  # Fallback

        if stat_template.fundamental_stats:
            attr_frame = ctk.CTkFrame(scroll_frame)
            attr_frame.pack(fill="x", padx=10, pady=5)
            ctk.CTkLabel(
                attr_frame, text="Attributes", font=Theme.fonts.subheading
            ).pack(fill="x", padx=5)
            for name, def_ in stat_template.fundamental_stats.items():
                val = abilities_data.get(name, def_.default)
                create_key_value_row(attr_frame, name, str(val))

        # Vitals
        vitals_data = self.character_data.get("vital_resources", {})
        if stat_template.vital_resources:
            for name, def_ in stat_template.vital_resources.items():
                data = vitals_data.get(name, {})
                curr = data.get("current", 0) if isinstance(data, dict) else data
                mx = data.get("max", 10) if isinstance(data, dict) else 10
                create_vital_display(scroll_frame, name, curr, mx)

        # Tracks / Consumables
        cons_data = self.character_data.get("consumable_resources", {})
        if stat_template.consumable_resources:
            for name, def_ in stat_template.consumable_resources.items():
                data = cons_data.get(name, {})
                val = data.get("current", 0) if isinstance(data, dict) else data
                mx = data.get("max", 0) if isinstance(data, dict) else 0
                create_track_display(scroll_frame, name, val, mx)

    def _render_raw_dict(self, parent, data):
        import json

        ctk.CTkLabel(
            parent,
            text=json.dumps(data, indent=2),
            justify="left",
            font=Theme.fonts.monospace,
        ).pack(fill="x")
