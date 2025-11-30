import logging
import customtkinter as ctk
from app.gui.styles import Theme
from app.tools.builtin._state_storage import get_versions, get_entity

logger = logging.getLogger(__name__)


class InventoryInspectorView(ctk.CTkFrame):
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.db_manager = db_manager
        self.orchestrator = None
        self.cached_ver = -1
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True)

    def refresh(self):
        if not self.orchestrator or not self.orchestrator.session:
            return
        sid = self.orchestrator.session.id

        vers = get_versions(sid, self.db_manager, "character")
        curr_ver = vers.get("player", 0)
        if curr_ver == self.cached_ver:
            return
        self.cached_ver = curr_ver

        entity = get_entity(sid, self.db_manager, "character", "player")
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

        collections_data = entity.get("collections", {})

        # Find collections assigned to 'equipment' panel
        for col_key, col_def in template.collections.items():
            if col_def.panel == "equipment":
                items = collections_data.get(col_key, [])
                self._render_collection(col_def.label, items, col_def.item_schema)

    def _render_collection(self, title, items, item_schema):
        # Header
        ctk.CTkLabel(
            self.scroll, text=f"{title} ({len(items)})", font=Theme.fonts.subheading
        ).pack(anchor="w", padx=10, pady=(10, 5))

        if not items:
            return

        for item in items:
            row = ctk.CTkFrame(self.scroll, fg_color=Theme.colors.bg_secondary)
            row.pack(fill="x", padx=5, pady=2)

            # Primary Label (Name) is usually first, or hardcoded 'name'
            name = item.get("name", "Item")

            # Left side: Name
            ctk.CTkLabel(row, text=name, font=("Arial", 12, "bold")).pack(
                side="left", padx=5
            )

            # Right side: Dynamic Schema Fields
            details = []

            # Always show Qty if > 1
            if item.get("qty", 1) > 1:
                details.append(f"x{item.get('qty')}")

            # Loop through schema for extras (e.g. Weight, Ammo, Quality)
            if item_schema:
                for field in item_schema:
                    if field.key in ["name", "qty"]:
                        continue  # Skip standard fields

                    val = item.get(field.key)
                    if val:
                        details.append(f"{field.label}: {val}")

            if details:
                ctk.CTkLabel(
                    row, text=" | ".join(details), text_color="gray", font=("Arial", 11)
                ).pack(side="right", padx=5)
