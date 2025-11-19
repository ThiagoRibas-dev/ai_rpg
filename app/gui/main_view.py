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
    InputManager,
)

# Other GUI components
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
        self.history_manager = None
        self.input_manager = None

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
        self.history_toolbar = None
        self.reroll_button = None
        self.delete_last_button = None
        self.trim_button = None
        self.history_info_label = None
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
        # COMMENT: Add a new attribute to hold the button reference.
        self.world_info_button = None

        self.authors_note_textbox = None
        self.inspector_selector = None
        self.inspector_container = None

        # Build UI
        self._setup_window()
        self._build_panels()
        self._init_managers()

    def _setup_window(self):
        """
        Configure main window properties.
        """
        self.title("AI-RPG")
        self.geometry(
            f"{Theme.dimensions.window_width}x{Theme.dimensions.window_height}"
        )

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
            parent=self, send_callback=self.handle_send_button
        )

        # Build control (right) panel
        control_widgets = ControlPanelBuilder.build(
            parent=self,
            prompt_callbacks={
                "new": self._stub_new_prompt,
                "edit": self._stub_edit_prompt,
                "delete": self._stub_delete_prompt,
            },
            session_callback=self._stub_new_game,
            save_context_callback=self.save_context,
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
        self.main_panel = main_widgets["main_panel"]
        self.game_time_label = main_widgets["game_time_label"]
        self.game_mode_label = main_widgets["game_mode_label"]
        self.session_name_label = main_widgets["session_name_label"]
        self.chat_history_frame = main_widgets["chat_history_frame"]
        self.choice_button_frame = main_widgets["choice_button_frame"]
        self.loading_frame = main_widgets["loading_frame"]
        self.loading_label = main_widgets["loading_label"]
        self.history_toolbar = main_widgets["history_toolbar"]
        self.reroll_button = main_widgets["reroll_button"]
        self.delete_last_button = main_widgets["delete_last_button"]
        self.trim_button = main_widgets["trim_button"]
        self.history_info_label = main_widgets["history_info_label"]
        self.user_input = main_widgets["user_input"]
        self.send_button = main_widgets["send_button"]
        self.stop_button = main_widgets["stop_button"]

        # Control panel widgets
        self.control_panel = control_widgets["control_panel"]
        self.prompt_collapsible = control_widgets["prompt_collapsible"]
        self.prompt_scrollable_frame = control_widgets["prompt_scrollable_frame"]
        self.prompt_new_button = control_widgets["prompt_new_button"]
        self.prompt_edit_button = control_widgets["prompt_edit_button"]
        self.prompt_delete_button = control_widgets["prompt_delete_button"]
        self.session_collapsible = control_widgets["session_collapsible"]
        self.session_scrollable_frame = control_widgets["session_scrollable_frame"]
        self.session_new_button = control_widgets["session_new_button"]
        # COMMENT: Store the new button reference when the UI is built.
        self.world_info_button = control_widgets["world_info_button"]

        self.authors_note_textbox = control_widgets["authors_note_textbox"]
        self.inspector_selector = control_widgets["inspector_selector"]
        self.inspector_container = control_widgets["inspector_container"]

    def _init_managers(self):
        """
        Initialize all manager instances.
        """
        # Chat bubble manager
        # REPLACES: Chat-related methods (lines 121-180)
        self.bubble_manager = ChatBubbleManager(self.chat_history_frame, self)

        # History manager (needs bubble_manager)
        # Note: Will set orchestrator in set_orchestrator()
        # (Can't initialize fully here because orchestrator doesn't exist yet)

        # Inspector manager (must be created before others reference it)
        # REPLACES: Inspector initialization (lines 390-450)
        self.inspector_manager = InspectorManager(
            self.db_manager, 
            self.inspector_container,
            self.inspector_selector
        )

        # Tool visualization manager
        # REPLACES: Tool visualization methods (lines 451-500)
        self.tool_viz_manager = ToolVisualizationManager(
            self.inspector_manager.tool_calls_frame
        )

        # Input manager (NEW)
        # This manager will handle user input, send button, and choices.
        # It needs the orchestrator, so it will be fully wired in set_orchestrator.
        # We can partially initialize it here with the widgets it needs.
        self.input_manager = InputManager(
            orchestrator=None, # Will be set later
            session_manager=None, # Will be set later
            user_input_widget=self.user_input,
            send_button_widget=self.send_button,
            choice_button_frame=self.choice_button_frame
        )

        # Session manager and UI queue handler will be initialized in set_orchestrator()
        # because they need the orchestrator instance

    def set_orchestrator(self, orchestrator):
        """
        Wire orchestrator to all managers.

        Args:
            orchestrator: Orchestrator instance
        """
        self.orchestrator = orchestrator

        # Prompt manager
        # REPLACES: Prompt methods (lines 621-700)
        self.prompt_manager = PromptManager(
            self.db_manager, 
            orchestrator, 
            self.prompt_scrollable_frame, 
            # Pass the main view as the parent for dialogs
            parent_view=self, 
            prompt_collapsible=self.prompt_collapsible
        )

        # Refresh prompt list
        self.prompt_manager.refresh_list()

        # Initialize history manager (needs orchestrator)
        from app.gui.managers.history_manager import HistoryManager

        self.history_manager = HistoryManager(
            orchestrator, self.db_manager, self.bubble_manager
        )

        # Initialize session manager (needs orchestrator)
        self.session_manager = SessionManager(
            orchestrator,
            self.db_manager,
            self.session_scrollable_frame,
            self.session_name_label,
            self.game_time_label,
            self.game_mode_label,
            self.send_button,
            self.session_collapsible,
            self.bubble_manager,
            self.authors_note_textbox,
            on_session_loaded_callback=self._on_session_loaded,
        )

        # Wire prompt manager to session manager
        # Enable cross-manager coordination
        self.prompt_manager.set_session_manager(self.session_manager)
        # COMMENT: Give the prompt manager a reference to the bubble manager for user feedback.
        self.prompt_manager.bubble_manager = self.bubble_manager

        # Wire input manager dependencies
        self.input_manager.orchestrator = orchestrator
        self.input_manager.session_manager = self.session_manager

        # Wire session manager button callbacks (late binding)
        # Connect session buttons to manager methods
        self.session_manager._on_button_click = (
            lambda s: self.session_manager.on_session_select(
                s,
                self.bubble_manager,
                {
                    "character": self.inspector_manager.character_inspector,
                    "inventory": self.inspector_manager.inventory_inspector,
                    "quest": self.inspector_manager.quest_inspector,
                    "memory": self.inspector_manager.memory_inspector,
                },
            )
        )

        # Initialize UI queue handler (needs orchestrator)
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
                "character": self.inspector_manager.character_inspector,
                "inventory": self.inspector_manager.inventory_inspector,
                "quest": self.inspector_manager.quest_inspector,
                "memory": self.inspector_manager.memory_inspector,
            },
        )
        self.ui_queue_handler.on_choice_selected = self.input_manager.handle_choice_selected

        # Wire inspectors
        self.inspector_manager.set_orchestrator(orchestrator)

        # Rewire button callbacks (from stubs to actual manager methods)
        self.prompt_new_button.configure(command=self.prompt_manager.new_prompt)
        self.prompt_edit_button.configure(command=self.prompt_manager.edit_prompt)
        self.prompt_delete_button.configure(command=self.prompt_manager.delete_prompt)
        # COMMENT: This is the new, robust line that REPLACES the fragile nametowidget call.
        self.world_info_button.configure(command=self.prompt_manager.open_lore_editor)
        self.session_new_button.configure(
            command=lambda: self.session_manager.new_game(
                self.prompt_manager.selected_prompt
            )
        )

        # Wire history control buttons
        self.reroll_button.configure(command=self.handle_reroll)
        self.delete_last_button.configure(command=self.handle_delete_last)
        self.trim_button.configure(command=self.handle_trim_history)

        # Start UI queue polling
        self.ui_queue_handler.start_polling()

        # Wire state viewer button
        self._wire_state_viewer_button()

    def _wire_state_viewer_button(self):
        """
        Wire the State Viewer button to actually open the dialog.

        - Replaces the stub in InspectorManager
        - Checks for active session before opening
        """
        # Find the State Viewer tab and replace button command
        state_viewer_frame = self.inspector_manager.views["State Viewer"]

        # Clear existing widgets (the stub button)
        for widget in state_viewer_frame.winfo_children():
            widget.destroy()

        # Create properly wired button
        ctk.CTkButton(
            state_viewer_frame,
            text="🔍 Open State Viewer",
            command=self._open_state_viewer,
            height=50,
        ).pack(expand=True)

    def _open_state_viewer(self):
        """
        Open the state viewer dialog with current session.

        - Checks for active session
        - Passes session_id and parent to InspectorManager
        """
        if not self.session_manager or not self.session_manager.selected_session:
            self.bubble_manager.add_message(
                "system", "⚠️ Please load a game session first"
            )
            return

        self.inspector_manager.open_state_viewer(
            self.session_manager.selected_session.id,
            self,  # parent window
        )

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
        # COMMENT: Delegated to the InputManager.
        return self.input_manager.get_input_text()

    def clear_input(self):
        """
        Clear user input field.
        """
        # COMMENT: Delegated to the InputManager.
        self.input_manager.clear_input_text()

    def handle_send_button(self):
        """Handle send button click."""
        # This logic is now fully owned by the InputManager.
        self.input_manager.handle_send_input()
        
    def select_choice(self, choice: str):
        """Handle when a user clicks an action choice."""
        # This logic is also fully owned by the InputManager.
        self.input_manager.handle_choice_selected(choice)

    def save_context(self):
        """
        Save author's note.
        """
        logger.debug("MainView.save_context() called")

        if not self.session_manager:
            logger.error("session_manager not initialized")
            return

        if not self.bubble_manager:
            logger.error("bubble_manager not initialized")
            return

        self.session_manager.save_context(self.bubble_manager)

    def log_tool_event(self, message: str):
        """
        Legacy method for tool event logging.
        """
        if hasattr(self, "orchestrator") and self.orchestrator:
            self.orchestrator.ui_queue.put({"type": "tool_event", "message": message})
        else:
            logger.warning(f"Orchestrator not set, cannot log tool event: {message}")

    def handle_reroll(self):
        """
        Reroll the last assistant response.
        """
        if not self.session_manager or not self.session_manager.selected_session:
            self.bubble_manager.add_message(
                "system", "⚠️ Please load a game session first"
            )
            return

        if not self.history_manager.can_reroll():
            self.bubble_manager.add_message(
                "system", "⚠️ Cannot reroll: last message is not from assistant"
            )
            return

        # Get the user message to resend
        user_message = self.history_manager.reroll_last_response(
            self.session_manager.selected_session
        )

        if user_message:
            # Add user message back to UI (it was already in history before the assistant response)
            # We don't need to add it again, just trigger regeneration

            # Disable send button during regeneration
            self.send_button.configure(state="disabled")

            # Clear any existing choices
            for widget in self.choice_button_frame.winfo_children():
                widget.destroy()
            self.choice_button_frame.grid_remove()

            # Trigger regeneration
            self.orchestrator.plan_and_execute(self.session_manager.selected_session)

        # Update history info
        self._update_history_info()

    def handle_delete_last(self):
        """
        Delete the last message pair (user + assistant).
        """
        if not self.session_manager or not self.session_manager.selected_session:
            self.bubble_manager.add_message(
                "system", "Please load a game session first"
            )
            return

        # Delete last 2 messages (user + assistant pair)
        success = self.history_manager.delete_last_n_messages(
            self.session_manager.selected_session, n=2
        )

        if success:
            self._update_history_info()

    def handle_trim_history(self):
        """
        Open dialog to delete last N messages.
        """
        if not self.session_manager or not self.session_manager.selected_session:
            self.bubble_manager.add_message(
                "system", "⚠️ Please load a game session first"
            )
            return

        current_length = self.history_manager.get_history_length()

        if current_length == 0:
            self.bubble_manager.add_message("system", "⚠️ No messages to delete")
            return

        # Simple input dialog for now
        dialog = ctk.CTkInputDialog(
            text=f"How many messages to delete? (1-{current_length})",
            title="Trim History",
        )
        result = dialog.get_input()

        if result:
            try:
                n = int(result)
                if n < 1 or n > current_length:
                    self.bubble_manager.add_message(
                        "system",
                        f"⚠️ Please enter a number between 1 and {current_length}",
                    )
                    return

                success = self.history_manager.delete_last_n_messages(
                    self.session_manager.selected_session, n=n
                )

                if success:
                    self._update_history_info()

            except ValueError:
                self.bubble_manager.add_message(
                    "system", "⚠️ Please enter a valid number"
                )

    def _update_history_info(self):
        """
        Update the history info label with current message count.
        """
        if self.history_manager:
            count = self.history_manager.get_history_length()
            self.history_info_label.configure(text=f"{count} messages")

    def _on_session_loaded(self):
        """
        Called when a session is successfully loaded.
        Shows history toolbar and updates info.
        """
        # Show history toolbar
        self.history_toolbar.grid()

        # Update history info
        self._update_history_info()
