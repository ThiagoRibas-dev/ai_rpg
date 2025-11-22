import logging

import customtkinter as ctk

# Builders
from app.gui.builders import (
    ControlPanelBuilder,
    InspectorPanelBuilder,
    MainPanelBuilder,
)

# Managers
from app.gui.managers import (
    ChatBubbleManager,
    InputManager,
    InspectorManager,
    PromptManager,
    SessionManager,
    ToolVisualizationManager,
    UIQueueHandler,
)
from app.gui.styles import Theme

logger = logging.getLogger(__name__)


class MainView(ctk.CTk):
    """
    Main application window with 3-column layout.
    Left: Inspectors
    Center: Chat
    Right: Management
    """

    def __init__(self, db_manager):
        super().__init__()

        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        self.orchestrator = None

        # Manager references
        self.bubble_manager = None
        self.tool_viz_manager = None
        self.ui_queue_handler = None
        self.session_manager = None
        self.prompt_manager = None
        self.inspector_manager = None
        self.history_manager = None
        self.input_manager = None

        # Widget references
        # Main panel (Center)
        self.main_panel = None
        self.game_time_label = None
        self.game_mode_label = None
        self.session_name_label = None
        self.chat_history_frame = None
        self.choice_button_frame = None
        self.loading_frame = None
        self.loading_label = None
        self.history_toolbar = None
        self.navigation_frame = None
        self.reroll_button = None
        self.delete_last_button = None
        self.trim_button = None
        self.history_info_label = None
        self.user_input = None
        self.send_button = None
        self.stop_button = None

        # Control panel (Right)
        self.control_panel = None
        self.prompt_collapsible = None
        self.prompt_scrollable_frame = None
        self.prompt_new_button = None
        self.prompt_edit_button = None
        self.prompt_delete_button = None
        self.session_collapsible = None
        self.session_scrollable_frame = None
        self.session_new_button = None
        self.world_info_button = None
        self.authors_note_textbox = None

        # Inspector panel (Left) - dict of containers
        self.inspector_containers = {}

        # Build UI
        self._setup_window()
        self._build_panels()
        self._init_managers()

    def _setup_window(self):
        """Configure main window grid."""
        self.title("AI-RPG")
        self.geometry(
            f"{Theme.dimensions.window_width}x{Theme.dimensions.window_height}"
        )

        # 3-Column Layout
        # Col 0: Inspectors (width 1)
        # Col 1: Chat (width 2 - wider)
        # Col 2: Controls (width 1)
        self.grid_columnconfigure(0, weight=25)
        self.grid_columnconfigure(1, weight=50)
        self.grid_columnconfigure(2, weight=25)
        self.grid_rowconfigure(0, weight=1)

    def _build_panels(self):
        """Construct UI panels."""

        # 1. Build Inspector Panel (Left - Col 0)
        self.inspector_containers = InspectorPanelBuilder.build(self, self.db_manager)

        # 2. Build Main Panel (Center - Col 1)
        main_widgets = MainPanelBuilder.build(
            parent=self, 
            send_callback=self.handle_send_button,
            zen_mode_callback=self.toggle_zen_mode # <--- PASS CALLBACK
        )

        # 3. Build Control Panel (Right - Col 2)
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
        # NEW: Store reference to the zen button if needed
        self.zen_button = main_widgets.get("zen_button")

    # --- NEW FEATURE: ZEN MODE ---
    def toggle_zen_mode(self):
        """
        Toggles the visibility of the left and right panels.
        """
        is_zen = getattr(self, "_is_zen_mode", False)
        
        if not is_zen:
            # Hide side panels
            self.inspector_containers["inspector_panel"].grid_remove()
            self.control_panel.grid_remove()
            
            # Expand center panel
            self.main_panel.grid(column=0, columnspan=3)
            
            # Update state
            self._is_zen_mode = True
            if self.zen_button:
                self.zen_button.configure(text="↩ Exit Zen", fg_color="gray30")
        else:
            # Restore side panels
            self.inspector_containers["inspector_panel"].grid()
            self.control_panel.grid()
            
            # Reset center panel
            self.main_panel.grid(column=1, columnspan=1)
            
            # Update state
            self._is_zen_mode = False
            if self.zen_button:
                self.zen_button.configure(text="🧘 Zen Mode", fg_color="transparent")

    def _store_widget_refs(self, main_widgets: dict, control_widgets: dict):
        """Store widget references from builders."""
        # Main panel
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
        self.navigation_frame = main_widgets.get("navigation_frame")

        # Control panel
        self.control_panel = control_widgets["control_panel"]
        self.prompt_collapsible = control_widgets["prompt_collapsible"]
        self.prompt_scrollable_frame = control_widgets["prompt_scrollable_frame"]
        self.prompt_new_button = control_widgets["prompt_new_button"]
        self.prompt_edit_button = control_widgets["prompt_edit_button"]
        self.prompt_delete_button = control_widgets["prompt_delete_button"]
        self.session_collapsible = control_widgets["session_collapsible"]
        self.session_scrollable_frame = control_widgets["session_scrollable_frame"]
        self.session_new_button = control_widgets["session_new_button"]
        self.world_info_button = control_widgets["world_info_button"]
        self.authors_note_textbox = control_widgets["authors_note_textbox"]

    def _init_managers(self):
        """Initialize managers."""
        self.bubble_manager = ChatBubbleManager(self.chat_history_frame, self)

        # Pass the inspector containers dict to the manager
        self.inspector_manager = InspectorManager(
            self.db_manager, self.inspector_containers
        )

        # The tool calls frame is now managed by InspectorManager inside 'tool_calls' key
        self.tool_viz_manager = ToolVisualizationManager(
            self.inspector_manager.views.get("tool_calls")
        )

        self.input_manager = InputManager(
            orchestrator=None,
            session_manager=None,
            user_input_widget=self.user_input,
            send_button_widget=self.send_button,
            choice_button_frame=self.choice_button_frame,
        )

    def set_orchestrator(self, orchestrator):
        """Wire orchestrator to managers."""
        self.orchestrator = orchestrator

        # Prompt Manager
        self.prompt_manager = PromptManager(
            self.db_manager,
            orchestrator,
            self.prompt_scrollable_frame,
            parent_view=self,
            prompt_collapsible=self.prompt_collapsible,
        )
        self.prompt_manager.refresh_list()
        self.prompt_manager.bubble_manager = self.bubble_manager

        # History Manager
        from app.gui.managers.history_manager import HistoryManager

        self.history_manager = HistoryManager(
            orchestrator, self.db_manager, self.bubble_manager
        )

        # Session Manager
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

        # Wire Prompt -> Session
        self.prompt_manager.set_session_manager(self.session_manager)

        # Wire Input -> Orchestrator
        self.input_manager.orchestrator = orchestrator
        self.input_manager.session_manager = self.session_manager

        # Wire Session selection to update inspectors
        # We map specific views from inspector_manager.views
        self.session_manager._on_button_click = (
            lambda s: self.session_manager.on_session_select(
                s,
                self.bubble_manager,
                {
                    "character": self.inspector_manager.views.get("character"),
                    "inventory": self.inspector_manager.views.get("inventory"),
                    "quest": self.inspector_manager.views.get("quest"),
                    "memory": self.inspector_manager.views.get("memory"),
                    "map": self.inspector_containers.get("map_panel"),
                },
            )
        )

        # UI Queue Handler
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
            self.navigation_frame,
            # Pass same views map
            {
                "character": self.inspector_manager.views.get("character"),
                "inventory": self.inspector_manager.views.get("inventory"),
                "quest": self.inspector_manager.views.get("quest"),
                "memory": self.inspector_manager.views.get("memory"),
                "map": self.inspector_containers.get("map_panel"),
            },
        )
        self.ui_queue_handler.on_choice_selected = (
            self.input_manager.handle_choice_selected
        )

        # Wire Inspectors
        self.inspector_manager.set_orchestrator(orchestrator)

        # Wire Control Buttons
        self.prompt_new_button.configure(command=self.prompt_manager.new_prompt)
        self.prompt_edit_button.configure(command=self.prompt_manager.edit_prompt)
        self.prompt_delete_button.configure(command=self.prompt_manager.delete_prompt)
        self.world_info_button.configure(command=self.prompt_manager.open_lore_editor)
        self.session_new_button.configure(command=self.open_setup_wizard)

        # Wire History Buttons
        self.reroll_button.configure(command=self.handle_reroll)
        self.delete_last_button.configure(command=self.handle_delete_last)
        self.trim_button.configure(command=self.handle_trim_history)

        # Wire State Viewer Button (in Left Panel now)
        self._wire_state_viewer_button()

        # Start Polling
        self.ui_queue_handler.start_polling()

    def open_setup_wizard(self):
        if not self.prompt_manager or not self.prompt_manager.selected_prompt:
            self.bubble_manager.add_message(
                "system", "⚠️ Please select a Prompt first to start a new game."
            )
            return
        selected_prompt = self.prompt_manager.selected_prompt
        self.session_manager.new_game(selected_prompt)

    def _wire_state_viewer_button(self):
        """Wire the State Viewer button (located in the Inspector/Debug panel)."""
        btn = self.inspector_manager.views.get("debug")
        if btn:
            btn.configure(command=self._open_state_viewer)

    def _open_state_viewer(self):
        if not self.session_manager or not self.session_manager.selected_session:
            self.bubble_manager.add_message(
                "system", "⚠️ Please load a game session first"
            )
            return
        self.inspector_manager.open_state_viewer(
            self.session_manager.selected_session.id, self
        )

    # --- Stubs & Delegation ---
    def _stub_new_prompt(self):
        logger.warning("Prompt manager not ready")

    def _stub_edit_prompt(self):
        logger.warning("Prompt manager not ready")

    def _stub_delete_prompt(self):
        logger.warning("Prompt manager not ready")

    def _stub_new_game(self):
        logger.warning("Session manager not ready")

    def get_input(self) -> str:
        return self.input_manager.get_input_text()

    def clear_input(self):
        self.input_manager.clear_input_text()

    def handle_send_button(self):
        self.input_manager.handle_send_input()

    def select_choice(self, choice: str):
        self.input_manager.handle_choice_selected(choice)

    def save_context(self):
        if self.session_manager:
            self.session_manager.save_context(self.bubble_manager)

    def log_tool_event(self, message: str):
        if hasattr(self, "orchestrator") and self.orchestrator:
            self.orchestrator.ui_queue.put({"type": "tool_event", "message": message})

    def handle_reroll(self):
        # Logic remains same, delegating to history_manager
        if not self.session_manager or not self.session_manager.selected_session:
            return
        if not self.history_manager.can_reroll():
            return

        user_message = self.history_manager.reroll_last_response(
            self.session_manager.selected_session
        )
        if user_message:
            self.send_button.configure(state="disabled")
            for widget in self.choice_button_frame.winfo_children():
                widget.destroy()
            self.choice_button_frame.grid_remove()
            self.orchestrator.plan_and_execute(self.session_manager.selected_session)
        self._update_history_info()

    def handle_delete_last(self):
        if not self.session_manager or not self.session_manager.selected_session:
            return
        if self.history_manager.delete_last_n_messages(
            self.session_manager.selected_session, n=2
        ):
            self._update_history_info()

    def handle_trim_history(self):
        # Logic remains same
        if not self.session_manager or not self.session_manager.selected_session:
            return
        current_len = self.history_manager.get_history_length()
        if current_len == 0:
            return
        dialog = ctk.CTkInputDialog(
            text=f"Delete how many? (1-{current_len})", title="Trim"
        )
        res = dialog.get_input()
        if res and res.isdigit():
            n = int(res)
            if 1 <= n <= current_len:
                if self.history_manager.delete_last_n_messages(
                    self.session_manager.selected_session, n
                ):
                    self._update_history_info()

    def _update_history_info(self):
        if self.history_manager:
            self.history_info_label.configure(
                text=f"{self.history_manager.get_history_length()} messages"
            )

    def _on_session_loaded(self):
        self.history_toolbar.grid()
        self._update_history_info()
