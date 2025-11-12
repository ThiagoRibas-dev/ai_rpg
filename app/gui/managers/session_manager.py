"""
Manages game session CRUD operations and UI.

New responsibilities:
- Create/load/save game sessions
- Handle session selection
- Update session context (memory, author's note)
- Coordinate with orchestrator
"""

import customtkinter as ctk
import logging
from datetime import datetime
from typing import Optional, Callable
from app.models.game_session import GameSession
from app.gui.styles import get_button_style
from app.gui.utils.ui_helpers import get_mode_display

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages game session operations and selection.
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
        session_collapsible,
        authors_note_textbox: ctk.CTkTextbox,
        on_session_loaded_callback: Optional[Callable] = None,
    ):
        """
        Initialize the session manager.

        Args:
            orchestrator: Orchestrator instance
            db_manager: Database manager instance
            session_scrollable_frame: Frame for displaying session list
            session_name_label: Label for current session name
            game_time_label: Label for current game time
            game_mode_label: Label for current game mode
            send_button: Send button to enable/disable
            session_collapsible: Collapsible frame container
            authors_note_textbox: Author's Notes textbox
            on_session_loaded_callback: Optional callback to run after session loads
        """
        self.orchestrator = orchestrator
        self.db_manager = db_manager
        self.session_scrollable_frame = session_scrollable_frame
        self.session_name_label = session_name_label
        self.game_time_label = game_time_label
        self.game_mode_label = game_mode_label
        self.send_button = send_button
        self.session_collapsible = session_collapsible
        self.authors_note_textbox = authors_note_textbox
        self._selected_session: Optional[GameSession] = None
        self.on_session_loaded_callback = on_session_loaded_callback

    @property
    def selected_session(self) -> Optional[GameSession]:
        """
        Get the currently selected session.
        """
        return self._selected_session

    def new_game(self, selected_prompt):
        """
        Create a new game session with initial GM message and scaffolding.

        UPDATED:
        - Adds initial_message from prompt as first assistant message
        - Injects SETUP scaffolding into game state
        - Displays initial message in chat immediately
        """
        if not selected_prompt:
            return

        # Generate timestamped session name
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        session_name = f"{timestamp}_{selected_prompt.name}"

        # Create session via orchestrator
        self.orchestrator.new_session(selected_prompt.content)

        # Add initial message if it exists
        if selected_prompt.initial_message and selected_prompt.initial_message.strip():
            self.orchestrator.session.add_message(
                "assistant", selected_prompt.initial_message
            )

        # Save to get session ID
        self.orchestrator.save_game(session_name, selected_prompt.id)

        # ✅ NEW: Inject SETUP scaffolding
        # if self.orchestrator.session.id:
        #     self._inject_setup_scaffolding(
        #         self.orchestrator.session.id, selected_prompt.content
        #     )

        # Refresh session list to show new session
        self.refresh_session_list(selected_prompt.id)

    def _inject_setup_scaffolding(self, session_id: int, prompt_content: str):
        """
        Inject initial scaffolding structure for SETUP mode.

        Args:
            session_id: Current session ID
            prompt_content: The prompt content (used for genre detection)
        """
        from app.core.scaffolding_templates import (
            get_setup_scaffolding,
            detect_genre_from_prompt,
            get_genre_specific_scaffolding,
        )

        # Detect genre and get appropriate scaffolding
        genre = detect_genre_from_prompt(prompt_content)

        if genre != "generic":
            scaffolding = get_genre_specific_scaffolding(genre)
        else:
            scaffolding = get_setup_scaffolding()

        # Inject scaffolding into database
        for entity_type, entities in scaffolding.items():
            for entity_key, entity_data in entities.items():
                self.db_manager.set_game_state_entity(
                    session_id, entity_type, entity_key, entity_data
                )

        logger.info(f"Injected {genre} scaffolding for session {session_id}")

    def load_game(self, session_id: int, bubble_manager):
        """
        Load a saved game session.

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

        Args:
            session: Selected session
            bubble_manager: ChatBubbleManager instance
            inspectors: Dictionary of inspector instances
        """
        self._selected_session = session
        self.load_game(session.id, bubble_manager)
        self.send_button.configure(state="normal")

        # Update header with session info
        self.session_name_label.configure(text=session.name)
        self.game_time_label.configure(text=f"🕐 {session.game_time}")

        # Update game mode indicator
        mode_text, mode_color = get_mode_display(session.game_mode)
        self.game_mode_label.configure(text=mode_text, text_color=mode_color)

        # Load context (Author's Note)
        self.load_context(self.authors_note_textbox)

        # Update memory inspector if available
        if "memory" in inspectors and inspectors["memory"]:
            inspectors["memory"].set_session(session.id)

        # Refresh all inspectors
        for inspector_name in ["character", "inventory", "quest"]:
            if inspector_name in inspectors and inspectors[inspector_name]:
                inspectors[inspector_name].refresh()

        # Update button styles
        button_styles = get_button_style()
        selected_style = get_button_style("selected")

        for widget in self.session_scrollable_frame.winfo_children():
            if widget.cget("text") == session.name:
                widget.configure(fg_color=selected_style["fg_color"])
            else:
                widget.configure(fg_color=button_styles["fg_color"])

        # Collapse the session panel
        if self.session_collapsible and not self.session_collapsible.is_collapsed:
            self.session_collapsible.toggle()

        # Notify MainView that session was loaded
        if self.on_session_loaded_callback:
            self.on_session_loaded_callback()

    def refresh_session_list(self, prompt_id: int | None = None):
        """
        Refresh the session list UI.

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
                    command=lambda s=session: self._on_button_click(s),
                )
                btn.pack(pady=2, padx=5, fill="x")

    def load_context(self, authors_note_textbox: ctk.CTkTextbox):
        """
        Load author's note for the current session.
        """
        import logging

        logger = logging.getLogger(__name__)

        if not self._selected_session:
            logger.debug("⏭️  No session selected, skipping load_context")
            return

        # Load context from database
        context = self.db_manager.get_session_context(self._selected_session.id)

        if context:
            # Populate author's note textbox
            authors_note = context.get("authors_note", "")
            authors_note_textbox.delete("1.0", "end")
            authors_note_textbox.insert("1.0", authors_note)

            logger.debug(
                f"📖 Loaded author's note ({len(authors_note)} chars) for session {self._selected_session.id}"
            )
        else:
            logger.warning(
                f"⚠️  No context found for session {self._selected_session.id}"
            )
            authors_note_textbox.delete("1.0", "end")

    def save_context(self, bubble_manager):
        """
        Save the author's note.

        MIGRATION NOTES:
        - Removed memory field (deprecated)
        """
        import logging

        logger = logging.getLogger(__name__)

        if not self._selected_session:
            logger.warning("❌ No session selected, cannot save context")
            bubble_manager.add_message("system", "⚠️ Please load a game session first")
            return

        try:
            # Get content from textbox
            authors_note = self.authors_note_textbox.get("1.0", "end-1c")

            logger.debug(
                f"💾 Saving author's note for session {self._selected_session.id}"
            )
            logger.debug(f"   Author's Note length: {len(authors_note)} chars")

            # Save to database (memory field = empty string)
            self.db_manager.update_session_context(
                self._selected_session.id,
                "",  # memory field always empty now
                authors_note,
            )

            logger.info(
                f"✅ Context saved successfully for session {self._selected_session.id}"
            )

            # Show confirmation
            bubble_manager.add_message("system", "✅ Author's Note saved")
        except Exception as e:
            logger.error(f"❌ Error saving context: {e}", exc_info=True)
            bubble_manager.add_message("system", f"❌ Error saving: {e}")

    def _on_button_click(self, session: GameSession):
        """
        Internal handler for session button clicks.
        """
        logger.warning("Session button clicked but dependencies not wired yet")
