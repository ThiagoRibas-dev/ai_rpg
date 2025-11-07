"""
Manages game session CRUD operations and UI.

MIGRATION SOURCE: main_view.py lines 501-620
Extracted methods:
- new_game() (lines 501-510)
- load_game() (lines 511-525)
- on_session_select() (lines 526-565)
- refresh_session_list() (lines 566-580)
- load_context() (lines 581-595)
- save_context() (lines 596-605)

New responsibilities:
- Create/load/save game sessions
- Handle session selection
- Update session context (memory, author's note)
- Coordinate with orchestrator
"""

import customtkinter as ctk
import logging
from datetime import datetime
from typing import Optional
from app.models.game_session import GameSession
from app.gui.styles import get_button_style
from app.gui.utils.ui_helpers import get_mode_display

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages game session operations and selection.
    
    MIGRATION NOTES:
    - Extracted from: MainView (session-related methods lines 501-620)
    - Requires orchestrator, bubble_manager for coordination
    - Manages session list UI and selection state
    """
    
    def __init__(
        self,
        orchestrator,
        db_manager,  # ✅ ADD THIS
        session_scrollable_frame: ctk.CTkScrollableFrame,
        session_name_label: ctk.CTkLabel,
        game_time_label: ctk.CTkLabel,
        game_mode_label: ctk.CTkLabel,
        send_button: ctk.CTkButton,
        session_collapsible
    ):
        """
        Initialize the session manager.
        
        MIGRATION NOTES:
        - All parameters previously accessed via self.* in MainView
        - orchestrator: Previously self.orchestrator
        - db_manager: Previously self.db_manager  # ✅ ADD THIS LINE
        - session_scrollable_frame: Previously self.session_scrollable_frame
        - Labels/buttons: Previously self.* references
        
        Args:
            orchestrator: Orchestrator instance
            db_manager: Database manager instance
            session_scrollable_frame: Frame for displaying session list
            session_name_label: Label for current session name
            game_time_label: Label for current game time
            game_mode_label: Label for current game mode
            send_button: Send button to enable/disable
            session_collapsible: Collapsible frame container
        """
        self.orchestrator = orchestrator
        self.db_manager = db_manager  # ✅ ADD THIS
        self.session_scrollable_frame = session_scrollable_frame
        self.session_name_label = session_name_label
        self.game_time_label = game_time_label
        self.game_mode_label = game_mode_label
        self.send_button = send_button
        self.session_collapsible = session_collapsible
        self._selected_session: Optional[GameSession] = None
    
    @property
    def selected_session(self) -> Optional[GameSession]:
        """
        Get the currently selected session.
        
        MIGRATION NOTES:
        - Previously: MainView.selected_session (line 29)
        - Now: Property on SessionManager
        """
        return self._selected_session
    
    def new_game(self, selected_prompt):
        """
        Create a new game session.
        
        MIGRATION NOTES:
        - Extracted from: MainView.new_game() lines 501-510
        - Changed: Direct orchestrator method calls (no self. prefix change)
        - Changed: self.refresh_session_list → self.refresh_session_list (no change)
        
        Args:
            selected_prompt: The prompt to use for this session
        """
        if not selected_prompt:
            return

        # Generate timestamped session name
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        session_name = f"{timestamp}_{selected_prompt.name}"

        # Create session via orchestrator
        self.orchestrator.new_session(selected_prompt.content)
        self.orchestrator.save_game(session_name, selected_prompt.id)
        
        # Refresh session list to show new session
        self.refresh_session_list(selected_prompt.id)
    
    def load_game(self, session_id: int, bubble_manager):
        """
        Load a saved game session.
        
        MIGRATION NOTES:
        - Extracted from: MainView.load_game() lines 511-525
        - Changed: Requires bubble_manager parameter (was self.bubble_manager)
        - Changed: self.clear_chat_history → bubble_manager.clear_history
        - Changed: self.add_message_bubble → bubble_manager.add_message
        
        Args:
            session_id: ID of the session to load
            bubble_manager: ChatBubbleManager instance for displaying history
        """
        # Load session via orchestrator
        self.orchestrator.load_game(session_id)
        
        # Clear existing chat
        bubble_manager.clear_history()
        
        # Replay history
        history = self.orchestrator.session.get_history()
        for message in history:
            if message.role == "user":
                bubble_manager.add_message("user", message.content)
            elif message.role == "assistant":
                bubble_manager.add_message("assistant", message.content)
            elif message.role == "system":
                bubble_manager.add_message("system", message.content)
    
    def on_session_select(self, session: GameSession, bubble_manager, inspectors: dict):
        """
        Handle session selection.
        
        MIGRATION NOTES:
        - Extracted from: MainView.on_session_select() lines 526-565
        - Changed: Requires bubble_manager and inspectors parameters
        - Changed: self._get_mode_display → get_mode_display (ui_helpers)
        - Changed: Inspector access via dict instead of self.*
        
        Args:
            session: Selected session
            bubble_manager: ChatBubbleManager instance
            inspectors: Dictionary of inspector instances
        """
        self._selected_session = session
        self.load_game(session.id, bubble_manager)
        self.send_button.configure(state="normal")
        
        # Update header with session info
        # MIGRATED FROM: lines 535-537
        self.session_name_label.configure(text=session.name)
        self.game_time_label.configure(text=f"🕐 {session.game_time}")
        
        # Update game mode indicator
        # MIGRATED FROM: lines 539-541
        # CHANGED: self._get_mode_display → get_mode_display
        mode_text, mode_color = get_mode_display(session.game_mode)
        self.game_mode_label.configure(text=mode_text, text_color=mode_color)
        
        # Update memory inspector if available
        # MIGRATED FROM: lines 543-545
        if 'memory' in inspectors and inspectors['memory']:
            inspectors['memory'].set_session(session.id)
        
        # Refresh all inspectors
        # MIGRATED FROM: lines 547-553
        for inspector_name in ['character', 'inventory', 'quest']:
            if inspector_name in inspectors and inspectors[inspector_name]:
                inspectors[inspector_name].refresh()
        
        # Update button styles
        # MIGRATED FROM: lines 555-562
        button_styles = get_button_style()
        selected_style = get_button_style("selected")
        
        for widget in self.session_scrollable_frame.winfo_children():
            if widget.cget("text") == session.name:
                widget.configure(fg_color=selected_style["fg_color"])
            else:
                widget.configure(fg_color=button_styles["fg_color"])
        
        # Collapse the session panel
        # MIGRATED FROM: lines 564-565
        if self.session_collapsible and not self.session_collapsible.is_collapsed:
            self.session_collapsible.toggle()
    
    def refresh_session_list(self, prompt_id: int | None = None):
        """
        Refresh the session list UI.
        
        MIGRATION NOTES:
        - Extracted from: MainView.refresh_session_list() lines 566-580
        - Changed: self._on_button_click needs to be wired externally
        - Uses stored reference to session_scrollable_frame
        
        Args:
            prompt_id: Filter sessions by prompt ID (optional)
        """
        # Clear existing widgets
        for widget in self.session_scrollable_frame.winfo_children():
            widget.destroy()

        if prompt_id:
            # Get sessions for this prompt
            sessions = self.db_manager.get_sessions_by_prompt(prompt_id)
            
            # Create button for each session
            for session in sessions:
                btn = ctk.CTkButton(
                    self.session_scrollable_frame, 
                    text=session.name,
                    command=lambda s=session: self._on_button_click(s)
                )
                btn.pack(pady=2, padx=5, fill="x")
    
    def load_context(self, memory_textbox: ctk.CTkTextbox, authors_note_textbox: ctk.CTkTextbox):
        """
        Load memory and author's note for the current session.
        
        MIGRATION NOTES:
        - Extracted from: MainView.load_context() lines 581-595
        - Changed: Requires textbox parameters (was self.*)
        - Uses orchestrator.db_manager instead of self.db_manager
        
        Args:
            memory_textbox: Textbox for memory content
            authors_note_textbox: Textbox for author's note
        """
        if not self._selected_session:
            return
        
        # Load context from database
        context = self.db_manager.get_session_context(self._selected_session.id)
        
        if context:
            # Populate memory textbox
            memory_textbox.delete("1.0", "end")
            memory_textbox.insert("1.0", context.get("memory", ""))
            
            # Populate author's note textbox
            authors_note_textbox.delete("1.0", "end")
            authors_note_textbox.insert("1.0", context.get("authors_note", ""))
    
    def save_context(
        self, 
        memory_textbox: ctk.CTkTextbox, 
        authors_note_textbox: ctk.CTkTextbox,
        bubble_manager
    ):
        """
        Save the current memory and author's note.
        
        MIGRATION NOTES:
        - Extracted from: MainView.save_context() lines 596-605
        - Changed: Requires textbox and bubble_manager parameters
        - Changed: self.add_message_bubble → bubble_manager.add_message
        
        Args:
            memory_textbox: Textbox containing memory content
            authors_note_textbox: Textbox containing author's note
            bubble_manager: ChatBubbleManager for showing confirmation
        """
        if not self._selected_session:
            return
        
        # Get content from textboxes
        memory = memory_textbox.get("1.0", "end-1c")
        authors_note = authors_note_textbox.get("1.0", "end-1c")
        
        # Save to database
        self.db_manager.update_session_context(
            self._selected_session.id, 
            memory, 
            authors_note
        )
        
        # Show confirmation
        bubble_manager.add_message("system", "Context saved")
    
    def _on_button_click(self, session: GameSession):
        """
        Internal handler for session button clicks.
        
        MIGRATION NOTES:
        - New method to handle button callbacks
        - Needs to be wired externally (bubble_manager, inspectors not available here)
        - MainView will provide a wrapper that calls on_session_select
        """
        logger.warning("Session button clicked but dependencies not wired yet")
