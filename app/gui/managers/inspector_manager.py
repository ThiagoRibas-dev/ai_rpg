"""
Manages game state inspector views.
Modified to handle simultaneous stacked views.
"""

import customtkinter as ctk
import logging
from typing import Dict
from app.gui.panels.inspectors.character_inspector import CharacterInspectorView
from app.gui.panels.inspectors.inventory_inspector import InventoryInspectorView
from app.gui.panels.inspectors.quest_inspector import QuestInspectorView
from app.gui.memory_inspector_view import MemoryInspectorView
from app.gui.styles import Theme

logger = logging.getLogger(__name__)


class InspectorManager:
    """
    Manages all game state inspector views in the left panel.
    """

    def __init__(self, db_manager, containers: Dict[str, ctk.CTkFrame]):
        """
        Initialize all inspector views into their provided containers.

        Args:
            db_manager: Database manager instance
            containers: Dictionary of frames from InspectorPanelBuilder
        """
        self.db_manager = db_manager
        self.containers = containers
        
        # Map to hold references to inspector instances
        self.views = {}

        # === Initialize Inspector Views ===

        # 1. Character Inspector
        if "character_container" in containers:
            self.character_inspector = CharacterInspectorView(
                containers["character_container"], self.db_manager
            )
            self.character_inspector.pack(fill="both", expand=True)
            self.views["character"] = self.character_inspector

        # 2. Inventory Inspector
        if "inventory_container" in containers:
            self.inventory_inspector = InventoryInspectorView(
                containers["inventory_container"], self.db_manager
            )
            self.inventory_inspector.pack(fill="both", expand=True)
            self.views["inventory"] = self.inventory_inspector

        # 3. Quest Inspector
        if "quest_container" in containers:
            self.quest_inspector = QuestInspectorView(
                containers["quest_container"], self.db_manager
            )
            self.quest_inspector.pack(fill="both", expand=True)
            self.views["quest"] = self.quest_inspector

        # 4. Memory Inspector
        if "memory_container" in containers:
            self.memory_inspector = MemoryInspectorView(
                containers["memory_container"],
                self.db_manager,
                None,  # Orchestrator set later
            )
            self.memory_inspector.pack(fill="both", expand=True)
            self.views["memory"] = self.memory_inspector

        # 5. Tool Calls (Log)
        if "tool_container" in containers:
            self.tool_calls_frame = ctk.CTkScrollableFrame(
                containers["tool_container"], fg_color=Theme.colors.bg_secondary, height=300
            )
            self.tool_calls_frame.pack(fill="both", expand=True)
            self.views["tool_calls"] = self.tool_calls_frame

        # 6. State Viewer Button (Debug)
        if "debug_container" in containers:
            self.state_viewer_button = ctk.CTkButton(
                containers["debug_container"],
                text="🐞 Open State Viewer",
                command=self._open_state_viewer_stub,
                height=30,
            )
            self.state_viewer_button.pack(fill="x", padx=5)
            self.views["debug"] = self.state_viewer_button

    def set_orchestrator(self, orchestrator):
        """
        Wire orchestrator to all inspectors.
        """
        if hasattr(self, 'character_inspector'):
            self.character_inspector.orchestrator = orchestrator
        if hasattr(self, 'inventory_inspector'):
            self.inventory_inspector.orchestrator = orchestrator
        if hasattr(self, 'quest_inspector'):
            self.quest_inspector.orchestrator = orchestrator
        if hasattr(self, 'memory_inspector'):
            self.memory_inspector.orchestrator = orchestrator

    def refresh_all(self):
        """
        Refresh all inspector views.
        """
        if hasattr(self, 'character_inspector'):
            self.character_inspector.refresh()
        if hasattr(self, 'inventory_inspector'):
            self.inventory_inspector.refresh()
        if hasattr(self, 'quest_inspector'):
            self.quest_inspector.refresh()
        if hasattr(self, 'memory_inspector'):
            self.memory_inspector.refresh_memories()

    def open_state_viewer(self, session_id: int, parent):
        """
        Open the state viewer dialog.
        """
        from app.gui.state_viewer_dialog import StateViewerDialog
        viewer = StateViewerDialog(parent, self.db_manager, session_id)
        viewer.grab_set()

    def _open_state_viewer_stub(self):
        """Stub, replaced by MainView."""
        logger.warning("State viewer button clicked but not wired")
