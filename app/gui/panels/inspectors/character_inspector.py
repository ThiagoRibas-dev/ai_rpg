import logging
import customtkinter as ctk
from app.gui.styles import Theme
from app.tools.builtin._state_storage import get_versions, get_entity
from .inspector_utils import render_widget, display_message_state

logger = logging.getLogger(__name__)


class CharacterInspectorView(ctk.CTkFrame):
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.db_manager = db_manager
        self.orchestrator = None
        self.current_key = "player"
        self.cached_ver = -1
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True)

    def refresh(self):
        if not self.orchestrator or not self.orchestrator.session:
            display_message_state(self.scroll, "No session.")
            return

        sid = self.orchestrator.session.id
        vers = get_versions(sid, self.db_manager, "character")
        curr_ver = vers.get(self.current_key, 0)
        if curr_ver == self.cached_ver:
            return
        self.cached_ver = curr_ver

        entity = get_entity(sid, self.db_manager, "character", self.current_key)
        if not entity:
            return

        tid = entity.get("template_id")
        template = self.db_manager.stat_templates.get_by_id(tid) if tid else None
        self._render(entity, template)

    def _render(self, entity, template):
        for w in self.scroll.winfo_children():
            w.destroy()
        if not template:
            return

        # 1. Header
        ctk.CTkLabel(
            self.scroll, text=entity.get("name", "Unknown"), font=Theme.fonts.heading
        ).pack(anchor="w", padx=10, pady=5)
        self._render_panel("header", entity, template)

        # 2. Split Body
        body = ctk.CTkFrame(self.scroll, fg_color="transparent")
        body.pack(fill="x", expand=True)
        side = ctk.CTkFrame(body, width=140, fg_color=Theme.colors.bg_tertiary)
        side.pack(side="left", fill="y", padx=5, pady=5)
        main = ctk.CTkFrame(body, fg_color="transparent")
        main.pack(side="right", fill="both", expand=True, padx=5)

        self._render_panel("sidebar", entity, template, parent=side)
        self._render_panel("main", entity, template, parent=main)

        for p in ["skills", "spells", "notes"]:
            self._render_panel(p, entity, template)

    def _render_panel(self, panel_name, entity, template, parent=None):
        if not parent:
            parent = self.scroll
        items = []

        # Fundamentals
        for key, def_ in template.fundamentals.items():
            if def_.panel == panel_name:
                val = entity.get("fundamentals", {}).get(key, def_.default)
                items.append((def_.group, def_.label, val, def_.widget, None))

        # Derived
        for key, def_ in template.derived.items():
            if def_.panel == panel_name:
                val = entity.get("derived", {}).get(key, def_.default)
                items.append((def_.group, def_.label, val, def_.widget, None))

        # Gauges
        for key, def_ in template.gauges.items():
            if def_.panel == panel_name:
                data = entity.get("gauges", {}).get(key, {})
                curr = data.get("current", 0) if isinstance(data, dict) else data
                mx = data.get("max", 10) if isinstance(data, dict) else 10
                items.append((def_.group, def_.label, curr, def_.widget, mx))

        if not items:
            return

        # Grouping
        grouped = {}
        for grp, lbl, val, wid, mx in items:
            grouped.setdefault(grp, []).append((lbl, val, wid, mx))

        for group_name, members in grouped.items():
            grp_frame = ctk.CTkFrame(parent, fg_color="transparent")
            grp_frame.pack(fill="x", pady=5)
            if group_name != "General":
                ctk.CTkLabel(
                    grp_frame,
                    text=group_name,
                    font=Theme.fonts.subheading,
                    text_color=Theme.colors.text_gold,
                ).pack(anchor="w", padx=5)
            for m in members:
                render_widget(grp_frame, *m)
