import customtkinter as ctk
import logging

# Builders (construct UI hierarchies)
from app.gui.builders import MainPanelBuilder, ControlPanelBuilder

# Managers (handle business logic)
from app.gui.managers import (
    ChatBubbleManager,
    ToolVisualizationManager,
    UIQueueHandler,
    SessionManager,
    PromptManager,
    InspectorManager,
)

# Other GUI components
from app.gui.world_info_manager_view import WorldInfoManagerView
from app.gui.styles import Theme

logger = logging.getLogger(__name__)


class MainView(ctk.CTk):
    """
    Main application window - coordinates UI builders and managers.
    
    ARCHITECTURE:
    - Builders create widget hierarchies (pure UI construction)
    - Managers handle business logic (state, events, coordination)
    - MainView wires everything together (orchestration only)
    """
    
    def __init__(self, db_manager):
        super().__init__()
        
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        self.orchestrator = None
        
        # Manager references (initialized in _init_managers)
        self.bubble_manager = None
        self.tool_viz_manager = None
        self.ui_queue_handler = None
        self.session_manager = None
        self.prompt_manager = None
        self.inspector_manager = None
        
        # Widget references (filled by builders in _build_panels)
        # Main panel widgets
        self.main_panel = None
        self.game_time_label = None
        self.game_mode_label = None
        self.session_name_label = None
        self.chat_history_frame = None
        self.choice_button_frame = None
        self.loading_frame = None
        self.loading_label = None
        self.user_input = None
        self.send_button = None
        self.stop_button = None
        
        # Control panel widgets
        self.control_panel = None
        self.prompt_collapsible = None
        self.prompt_scrollable_frame = None
        self.prompt_new_button = None
        self.prompt_edit_button = None
        self.prompt_delete_button = None
        self.session_collapsible = None
        self.session_scrollable_frame = None
        self.session_new_button = None

        self.authors_note_textbox = None
        self.game_state_inspector_tabs = None
        
        # Build UI
        self._setup_window()
        self._build_panels()
        self._init_managers()
    
    def _setup_window(self):
        """
        Configure main window properties.
        """
        self.title("AI-RPG")
        self.geometry(f"{Theme.dimensions.window_width}x{Theme.dimensions.window_height}")
        
        # Setup grid layout
        self.grid_columnconfigure(0, weight=6)  # Main panel (wider)
        self.grid_columnconfigure(1, weight=1)  # Control panel
        self.grid_rowconfigure(0, weight=1)
    
    def _build_panels(self):
        """
        Use builder classes to construct UI panels.
        """
        # Build main (left) panel
        main_widgets = MainPanelBuilder.build(
            parent=self,
            send_callback=self.handle_send_button
        )
        
        # Build control (right) panel
        control_widgets = ControlPanelBuilder.build(
            parent=self,
            prompt_callbacks={
                'new': self._stub_new_prompt,
                'edit': self._stub_edit_prompt,
                'delete': self._stub_delete_prompt,
            },
            session_callback=self._stub_new_game,
            world_info_callback=self.open_world_info_manager,
            save_context_callback=self.save_context
        )
        
        # Store widget references
        self._store_widget_refs(main_widgets, control_widgets)
    
    def _store_widget_refs(self, main_widgets: dict, control_widgets: dict):
        """
        Store widget references from builders.
        
        Args:
            main_widgets: Dictionary from MainPanelBuilder
            control_widgets: Dictionary from ControlPanelBuilder
        """
        # Main panel widgets
        self.main_panel = main_widgets['main_panel']
        self.game_time_label = main_widgets['game_time_label']
        self.game_mode_label = main_widgets['game_mode_label']
        self.session_name_label = main_widgets['session_name_label']
        self.chat_history_frame = main_widgets['chat_history_frame']
        self.choice_button_frame = main_widgets['choice_button_frame']
        self.loading_frame = main_widgets['loading_frame']
        self.loading_label = main_widgets['loading_label']
        self.user_input = main_widgets['user_input']
        self.send_button = main_widgets['send_button']
        self.stop_button = main_widgets['stop_button']
        
        # Control panel widgets
        self.control_panel = control_widgets['control_panel']
        self.prompt_collapsible = control_widgets['prompt_collapsible']
        self.prompt_scrollable_frame = control_widgets['prompt_scrollable_frame']
        self.prompt_new_button = control_widgets['prompt_new_button']
        self.prompt_edit_button = control_widgets['prompt_edit_button']
        self.prompt_delete_button = control_widgets['prompt_delete_button']
        self.session_collapsible = control_widgets['session_collapsible']
        self.session_scrollable_frame = control_widgets['session_scrollable_frame']
        self.session_new_button = control_widgets['session_new_button']

        self.authors_note_textbox = control_widgets['authors_note_textbox']
        self.game_state_inspector_tabs = control_widgets['game_state_inspector_tabs']
    
    def _init_managers(self):
        """
        Initialize all manager instances.
        """
        # Chat bubble manager
        # REPLACES: Chat-related methods (lines 121-180)
        self.bubble_manager = ChatBubbleManager(self.chat_history_frame, self)
        
        # Inspector manager (must be created before others reference it)
        # REPLACES: Inspector initialization (lines 390-450)
        self.inspector_manager = InspectorManager(
            self.db_manager,
            self.game_state_inspector_tabs
        )
        
        # Tool visualization manager
        # REPLACES: Tool visualization methods (lines 451-500)
        self.tool_viz_manager = ToolVisualizationManager(
            self.inspector_manager.tool_calls_frame
        )
        
        # Prompt manager
        # REPLACES: Prompt methods (lines 621-700)
        self.prompt_manager = PromptManager(
            self.db_manager,
            self.prompt_scrollable_frame,
            self.prompt_collapsible
        )
        
        # Refresh prompt list
        self.prompt_manager.refresh_list()
        
        # Session manager and UI queue handler will be initialized in set_orchestrator()
        # because they need the orchestrator instance
    
    def set_orchestrator(self, orchestrator):
        """
        Wire orchestrator to all managers.
        
        Args:
            orchestrator: Orchestrator instance
        """
        self.orchestrator = orchestrator
        
        # Initialize session manager (needs orchestrator)
        # REPLACES: Session methods (lines 501-620)
        self.session_manager = SessionManager(
            orchestrator,
            self.db_manager,  # ✅ ADD THIS
            self.session_scrollable_frame,
            self.session_name_label,
            self.game_time_label,
            self.game_mode_label,
            self.send_button,
            self.session_collapsible
        )
        
        # Wire prompt manager to session manager
        # NEW: Enable cross-manager coordination
        self.prompt_manager.set_session_manager(self.session_manager)
        
        # Wire session manager button callbacks (late binding)
        # NEW: Connect session buttons to manager methods
        self.session_manager._on_button_click = lambda s: self.session_manager.on_session_select(
            s, 
            self.bubble_manager,
            {
                'character': self.inspector_manager.character_inspector,
                'inventory': self.inspector_manager.inventory_inspector,
                'quest': self.inspector_manager.quest_inspector,
                'memory': self.inspector_manager.memory_inspector
            }
        )
        
        # Initialize UI queue handler (needs orchestrator)
        # REPLACES: UI queue methods (lines 181-280)
        self.ui_queue_handler = UIQueueHandler(
            orchestrator,
            self.bubble_manager,
            self.tool_viz_manager,
            self.loading_frame,
            self.loading_label,
            self.choice_button_frame,
            self.send_button,
            self.game_time_label,
            self.game_mode_label,
            {
                'character': self.inspector_manager.character_inspector,
                'inventory': self.inspector_manager.inventory_inspector,
                'quest': self.inspector_manager.quest_inspector,
                'memory': self.inspector_manager.memory_inspector
            }
        )
        self.ui_queue_handler.on_choice_selected = self.select_choice
        
        # Wire inspectors
        self.inspector_manager.set_orchestrator(orchestrator)
        
        # Rewire button callbacks (from stubs to actual manager methods)
        # NEW: Replace stub callbacks with real ones
        self.prompt_new_button.configure(command=self.prompt_manager.new_prompt)
        self.prompt_edit_button.configure(command=self.prompt_manager.edit_prompt)
        self.prompt_delete_button.configure(command=self.prompt_manager.delete_prompt)
        self.session_new_button.configure(
            command=lambda: self.session_manager.new_game(self.prompt_manager.selected_prompt)
        )
        
        # Start UI queue polling
        # REPLACES: self.after(100, self._process_ui_queue) (line 112)
        self.ui_queue_handler.start_polling()
    
    # ==================== Stub methods for callbacks ====================
    # These are used during UI construction (before managers exist)
    # They are replaced in set_orchestrator() with actual manager methods
    
    def _stub_new_prompt(self):
        """Stub - replaced in set_orchestrator()."""
        logger.warning("Prompt new button clicked before manager initialization")
    
    def _stub_edit_prompt(self):
        """Stub - replaced in set_orchestrator()."""
        logger.warning("Prompt edit button clicked before manager initialization")
    
    def _stub_delete_prompt(self):
        """Stub - replaced in set_orchestrator()."""
        logger.warning("Prompt delete button clicked before manager initialization")
    
    def _stub_new_game(self):
        """Stub - replaced in set_orchestrator()."""
        logger.warning("New game button clicked before manager initialization")
    
    # ==================== Thin delegation methods ====================
    # These remain for external callers (orchestrator, etc.)
    # They delegate to the appropriate manager
    
    def get_input(self) -> str:
        """
        Get user input text.
        """
        return self.user_input.get("1.0", "end-1c")
    
    def clear_input(self):
        """
        Clear user input field.
        """
        self.user_input.delete("1.0", "end")
    
    def handle_send_button(self):
        """
        Handle send button click.
        """
        if not self.session_manager or not self.session_manager.selected_session:
            return
        
        # Disable to prevent concurrent turns
        self.send_button.configure(state="disabled")
        
        # Clear previous choices
        for widget in self.choice_button_frame.winfo_children():
            widget.destroy()
        self.choice_button_frame.grid_remove()
        
        # Start turn (non-blocking)
        self.orchestrator.plan_and_execute(self.session_manager.selected_session)
    
    def select_choice(self, choice: str):
        """
        Handle when a user clicks an action choice.
        
        Args:
            choice: Selected choice text
        """
        self.user_input.delete("1.0", "end")
        self.user_input.insert("1.0", choice)
        self.choice_button_frame.grid_remove()
        self.handle_send_button()
    
    def save_context(self):
        """
        Save memory and author's note.
        """
        if self.session_manager:
            self.session_manager.save_context(
                self.authors_note_textbox,
                self.bubble_manager
            )
    
    def open_world_info_manager(self):
        """
        Open world info manager dialog.
        """
        if not self.prompt_manager.selected_prompt:
            self.bubble_manager.add_message("system", "Please select a prompt first")
            return
        
        world_info_view = WorldInfoManagerView(
            self, 
            self.db_manager, 
            self.prompt_manager.selected_prompt.id, 
            getattr(self.orchestrator, "vector_store", None)
        )
        world_info_view.grab_set()
    
    def log_tool_event(self, message: str):
        """
        Legacy method for tool event logging.
        """
        if hasattr(self, 'orchestrator') and self.orchestrator:
            self.orchestrator.ui_queue.put({"type": "tool_event", "message": message})
        else:
            logger.warning(f"Orchestrator not set, cannot log tool event: {message}")