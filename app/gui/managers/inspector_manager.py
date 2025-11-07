"""
Manages game state inspector views.

MIGRATION SOURCE: main_view.py lines 701-730
Extracted logic:
- Inspector tab creation (lines 390-450)
- Inspector view initialization (lines 400-440)
- set_orchestrator() inspector wiring (lines 780-790)
- open_state_viewer() (lines 720-730)

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
    QuestInspectorView
)
from app.gui.memory_inspector_view import MemoryInspectorView
from app.gui.styles import Theme

logger = logging.getLogger(__name__)


class InspectorManager:
    """
    Manages all game state inspector views.
    
    MIGRATION NOTES:
    - Extracted from: MainView (inspector initialization and coordination)
    - Original inspector creation in _create_right_panel_widgets (lines 390-450)
    - Original orchestrator wiring in set_orchestrator (lines 780-790)
    - Centralizes all inspector management
    """
    
    def __init__(self, db_manager, tabs: ctk.CTkTabview):
        """
        Initialize all inspector views.
        
        MIGRATION NOTES:
        - Extracted from: MainView._create_right_panel_widgets() lines 390-450
        - db_manager: Previously self.db_manager
        - tabs: Previously self.game_state_inspector_tabs
        - Creates all inspector instances
        - Creates tool_calls_frame (used by ToolVisualizationManager)
        
        Args:
            db_manager: Database manager instance
            tabs: TabView widget to create inspector tabs in
        """
        self.db_manager = db_manager
        self.tabs = tabs
        
        # === Initialize Inspector Views ===
        # MIGRATED FROM: lines 400-420
        
        # Character inspector
        self.character_inspector = CharacterInspectorView(
            self.tabs.tab("Characters"),
            self.db_manager
        )
        self.character_inspector.pack(fill="both", expand=True)
        
        # Inventory inspector
        self.inventory_inspector = InventoryInspectorView(
            self.tabs.tab("Inventory"),
            self.db_manager
        )
        self.inventory_inspector.pack(fill="both", expand=True)
        
        # Quest inspector
        self.quest_inspector = QuestInspectorView(
            self.tabs.tab("Quests"),
            self.db_manager
        )
        self.quest_inspector.pack(fill="both", expand=True)
        
        # Memory inspector
        # MIGRATED FROM: lines 422-428
        self.memory_inspector = MemoryInspectorView(
            self.tabs.tab("Memories"),
            self.db_manager,
            None  # Orchestrator will be set later
        )
        self.memory_inspector.pack(fill="both", expand=True)
        
        # Tool calls frame (used by ToolVisualizationManager)
        # MIGRATED FROM: lines 430-435
        self.tool_calls_frame = ctk.CTkScrollableFrame(
            self.tabs.tab("Tool Calls"),
            fg_color=Theme.colors.bg_secondary
        )
        self.tool_calls_frame.pack(fill="both", expand=True)
        
        # State viewer button
        # MIGRATED FROM: lines 437-445
        state_viewer_frame = self.tabs.tab("State Viewer")
        ctk.CTkButton(
            state_viewer_frame,
            text="🔍 Open State Viewer",
            command=self._open_state_viewer_stub,
            height=50
        ).pack(expand=True)
    
    def set_orchestrator(self, orchestrator):
        """
        Wire orchestrator to all inspectors.
        
        MIGRATION NOTES:
        - Extracted from: MainView.set_orchestrator() lines 780-790
        - Simplified: No conditional checks (inspectors always exist)
        
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
        
        MIGRATION NOTES:
        - Extracted from: MainView.open_state_viewer() lines 720-730
        - Changed: Requires session_id parameter (was self.selected_session.id)
        - Changed: Requires parent parameter (was self)
        
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
