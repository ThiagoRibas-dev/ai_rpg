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
# COMMENT: Imports are updated to point to the new, modularized inspector files.
from app.gui.panels.inspectors.character_inspector import CharacterInspectorView
from app.gui.panels.inspectors.inventory_inspector import InventoryInspectorView
from app.gui.panels.inspectors.quest_inspector import QuestInspectorView
from app.gui.memory_inspector_view import MemoryInspectorView
from app.gui.styles import Theme

logger = logging.getLogger(__name__)


class InspectorManager:
    """
    Manages all game state inspector views.
    """

    def __init__(self, db_manager, container: ctk.CTkFrame, selector: ctk.CTkOptionMenu):
        """
        Initialize all inspector views.

        Args:
            db_manager: Database manager instance
            container: The frame where views will be packed
            selector: The dropdown menu to switch views
        """
        self.db_manager = db_manager
        self.container = container
        self.selector = selector
        self.views = {} 

        # === Initialize Inspector Views ===

        # === Initialize Inspector Views ===

        # Character inspector
        self.character_inspector = CharacterInspectorView(
            self.container, self.db_manager
        )
        self.views["Character"] = self.character_inspector

        # Inventory inspector
        self.inventory_inspector = InventoryInspectorView(
            self.container, self.db_manager
        )
        self.views["Inventory"] = self.inventory_inspector

        # Quest inspector
        self.quest_inspector = QuestInspectorView(
            self.container, self.db_manager
        )
        self.views["Quests"] = self.quest_inspector

        # Memory inspector
        self.memory_inspector = MemoryInspectorView(
            self.container,
            self.db_manager,
            None,  # Orchestrator will be set later
        )
        self.views["Memories"] = self.memory_inspector

        # Tool calls frame (used by ToolVisualizationManager)
        self.tool_calls_frame = ctk.CTkScrollableFrame(
            self.container, fg_color=Theme.colors.bg_secondary
        )
        self.views["Tool Calls"] = self.tool_calls_frame

        # State viewer button
        state_viewer_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        ctk.CTkButton(
            state_viewer_frame,
            text="ðŸ”  Open State Viewer",
            command=self._open_state_viewer_stub,
            height=50,
        ).pack(expand=True, pady=20)
        self.views["State Viewer"] = state_viewer_frame

        # === Configure Selector ===
        view_names = list(self.views.keys())
        self.selector.configure(values=view_names, command=self.switch_view)
        
        # Default to Character view
        self.selector.set("Character")
        self.switch_view("Character")

    def switch_view(self, view_name: str):
        """Hides the current view and shows the selected one."""
        # Hide all views
        for view in self.views.values():
            view.pack_forget()

        # Show selected view
        if view_name in self.views:
            self.views[view_name].pack(fill="both", expand=True, padx=2, pady=2)

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
