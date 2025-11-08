"""
Manages game state inspector views.

New responsibilities:
- Initialize all inspector views
- Coordinate inspector refreshes
- Open state viewer dialog
- Wire orchestrator to inspectors
"""

import customtkinter as ctk
import logging
from app.gui.state_inspector_views import (
    CharacterInspectorView,
    InventoryInspectorView,
    QuestInspectorView,
)
from app.gui.memory_inspector_view import MemoryInspectorView
from app.gui.styles import Theme

logger = logging.getLogger(__name__)


class InspectorManager:
    """
    Manages all game state inspector views.
    """

    def __init__(self, db_manager, tabs: ctk.CTkTabview):
        """
        Initialize all inspector views.

        Args:
            db_manager: Database manager instance
            tabs: TabView widget to create inspector tabs in
        """
        self.db_manager = db_manager
        self.tabs = tabs

        # === Initialize Inspector Views ===

        # Character inspector
        self.character_inspector = CharacterInspectorView(
            self.tabs.tab("Characters"), self.db_manager
        )
        self.character_inspector.pack(fill="both", expand=True)

        # Inventory inspector
        self.inventory_inspector = InventoryInspectorView(
            self.tabs.tab("Inventory"), self.db_manager
        )
        self.inventory_inspector.pack(fill="both", expand=True)

        # Quest inspector
        self.quest_inspector = QuestInspectorView(
            self.tabs.tab("Quests"), self.db_manager
        )
        self.quest_inspector.pack(fill="both", expand=True)

        # Memory inspector
        self.memory_inspector = MemoryInspectorView(
            self.tabs.tab("Memories"),
            self.db_manager,
            None,  # Orchestrator will be set later
        )
        self.memory_inspector.pack(fill="both", expand=True)

        # Tool calls frame (used by ToolVisualizationManager)
        self.tool_calls_frame = ctk.CTkScrollableFrame(
            self.tabs.tab("Tool Calls"), fg_color=Theme.colors.bg_secondary
        )
        self.tool_calls_frame.pack(fill="both", expand=True)

        # State viewer button
        state_viewer_frame = self.tabs.tab("State Viewer")
        ctk.CTkButton(
            state_viewer_frame,
            text="🔍 Open State Viewer",
            command=self._open_state_viewer_stub,
            height=50,
        ).pack(expand=True)

    def set_orchestrator(self, orchestrator):
        """
        Wire orchestrator to all inspectors.

        Args:
            orchestrator: Orchestrator instance
        """
        self.character_inspector.orchestrator = orchestrator
        self.inventory_inspector.orchestrator = orchestrator
        self.quest_inspector.orchestrator = orchestrator
        self.memory_inspector.orchestrator = orchestrator

    def refresh_all(self):
        """
        Refresh all inspector views.

        NEW METHOD:
        - Convenience method to refresh all inspectors at once
        - Called when: Session is loaded or game state changes
        """
        self.character_inspector.refresh()
        self.inventory_inspector.refresh()
        self.quest_inspector.refresh()

    def open_state_viewer(self, session_id: int, parent):
        """
        Open the state viewer dialog.

        Args:
            session_id: Current session ID
            parent: Parent window for the dialog
        """
        from app.gui.state_viewer_dialog import StateViewerDialog

        viewer = StateViewerDialog(parent, self.db_manager, session_id)
        viewer.grab_set()

    def _open_state_viewer_stub(self):
        """
        Stub for state viewer button - needs to be wired externally.

        NEW METHOD:
        - Called by: State Viewer tab button
        - Needs session_id which isn't available here
        - MainView will wire this properly after initialization
        """
        logger.warning("State viewer button clicked but session_id not available")
