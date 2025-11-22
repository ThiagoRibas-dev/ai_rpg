"""
Builds the inspector (left) panel of the application.
Contains stacked collapsible frames for Character, Inventory, Quests, etc.
"""

import customtkinter as ctk
from typing import Dict, Any
from app.database.db_manager import DBManager
from app.gui.collapsible_frame import CollapsibleFrame
from app.gui.panels.map_panel import MapPanel
from app.gui.styles import Theme


class InspectorPanelBuilder:
    """
    Static factory for building the inspector (left) panel.
    """

    @staticmethod
    def build(parent: ctk.CTk, db_manager: DBManager) -> Dict[str, Any]:
        """
        Build the inspector panel and return container references.

        Args:
            parent: The main window
            db_manager: The database manager instance

        Returns:
            Dictionary containing references to the content frames of each section.
        """
        # === Inspector Panel (Scrollable to handle many open panels) ===
        inspector_panel = ctk.CTkScrollableFrame(parent, fg_color=Theme.colors.bg_primary)
        inspector_panel.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(Theme.spacing.padding_md, 0),
            pady=Theme.spacing.padding_md,
        )

        # Common pack config
        pack_config = {
            "pady": Theme.spacing.padding_sm,
            "padx": Theme.spacing.padding_sm,
            "fill": "x",
            "expand": False,
        }

        # === 1. Character ===
        char_collapsible = CollapsibleFrame(inspector_panel, "Character")
        char_collapsible.pack(**pack_config)
        # Default open
        
        # === 2. Inventory ===
        inv_collapsible = CollapsibleFrame(inspector_panel, "Inventory")
        inv_collapsible.pack(**pack_config)

        # === 3. Quests ===
        quest_collapsible = CollapsibleFrame(inspector_panel, "Quests")
        quest_collapsible.pack(**pack_config)

        # === 4. Map ===
        map_collapsible = CollapsibleFrame(inspector_panel, "World Map")
        map_collapsible.pack(**pack_config)
        map_panel = MapPanel(map_collapsible.get_content_frame(), db_manager=db_manager)
        map_panel.pack(fill="both", expand=True)

        # === 5. Memories ===
        mem_collapsible = CollapsibleFrame(inspector_panel, "Recent Memories")
        mem_collapsible.pack(**pack_config)
        mem_collapsible.toggle() # Default closed

        # === 6. Tool Log / Debug ===
        tool_collapsible = CollapsibleFrame(inspector_panel, "Tool Log")
        tool_collapsible.pack(**pack_config)
        tool_collapsible.toggle() # Default closed

        # === 7. State Viewer Button Area ===
        debug_frame = ctk.CTkFrame(inspector_panel, fg_color="transparent")
        debug_frame.pack(pady=10, fill="x")

        return {
            "inspector_panel": inspector_panel,
            "character_container": char_collapsible.get_content_frame(),
            "inventory_container": inv_collapsible.get_content_frame(),
            "quest_container": quest_collapsible.get_content_frame(),
            "map_panel": map_panel,
            "memory_container": mem_collapsible.get_content_frame(),
            "tool_container": tool_collapsible.get_content_frame(),
            "debug_container": debug_frame,
        }