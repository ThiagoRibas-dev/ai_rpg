# File: app/gui/managers/input_manager.py
# --- NEW FILE ---

import customtkinter as ctk
import logging

logger = logging.getLogger(__name__)

class InputManager:
    """
    Manages user input, the send button, and action choice selection.
    This class centralizes logic previously handled by MainView.
    """

    def __init__(self, orchestrator, session_manager, user_input_widget: ctk.CTkTextbox, send_button_widget: ctk.CTkButton, choice_button_frame: ctk.CTkFrame):
        """
        Initializes the InputManager.

        Args:
            orchestrator: The main orchestrator instance.
            session_manager: The SessionManager to get the active session.
            user_input_widget: The CTkTextbox for user input.
            send_button_widget: The CTkButton for sending messages.
            choice_button_frame: The CTkFrame that holds action choices.
        """
        self.orchestrator = orchestrator
        self.session_manager = session_manager
        self.user_input = user_input_widget
        self.send_button = send_button_widget
        self.choice_button_frame = choice_button_frame

    def handle_send_input(self):
        """
        Handles the send button click.
        This logic was moved from MainView.handle_send_button.
        """
        # COMMENT: This entire method is a direct move from MainView.
        # It ensures that input handling is self-contained.
        if not self.session_manager or not self.session_manager.selected_session:
            logger.warning("Send clicked but no active session.")
            return

        # Disable to prevent concurrent turns
        self.send_button.configure(state="disabled")

        # Clear previous choices
        for widget in self.choice_button_frame.winfo_children():
            widget.destroy()
        self.choice_button_frame.grid_remove()

        # Start turn (non-blocking)
        self.orchestrator.plan_and_execute(self.session_manager.selected_session)

    def handle_choice_selected(self, choice: str):
        """
        Handles when a user clicks an action choice.
        This logic was moved from MainView.select_choice.

        Args:
            choice: Selected choice text.
        """
        # COMMENT: This method was also moved from MainView, centralizing
        # how user actions are processed.
        self.user_input.delete("1.0", "end")
        self.user_input.insert("1.0", choice)
        self.choice_button_frame.grid_remove()
        self.handle_send_input()

    def get_input_text(self) -> str:
        """Gets the text from the user input widget."""
        return self.user_input.get("1.0", "end-1c")

    def clear_input_text(self):
        """Clears the user input widget."""
        self.user_input.delete("1.0", "end")
