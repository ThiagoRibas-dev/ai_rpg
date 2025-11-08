"""
Manages chat history manipulation (reroll, delete, trim).
"""

import logging
from typing import Optional
from app.models.game_session import GameSession

logger = logging.getLogger(__name__)


class HistoryManager:
    """
    Handles chat history editing operations.

    Responsibilities:
    - Delete last N messages from Session.history
    - Update GameSession in database
    - Clear corresponding UI bubbles
    - Trigger regeneration for reroll
    """

    def __init__(self, orchestrator, db_manager, bubble_manager):
        """
        Args:
            orchestrator: Orchestrator instance (has Session)
            db_manager: Database manager
            bubble_manager: ChatBubbleManager for UI updates
        """
        self.orchestrator = orchestrator
        self.db_manager = db_manager
        self.bubble_manager = bubble_manager

    def can_reroll(self) -> bool:
        """
        Check if reroll is possible (last message is from assistant).

        Returns:
            True if last message is from assistant
        """
        if not self.orchestrator.session:
            return False

        history = self.orchestrator.session.get_history()
        if not history:
            return False

        return history[-1].role == "assistant"

    def can_delete(self, n: int = 1) -> bool:
        """
        Check if deletion is possible.

        Args:
            n: Number of messages to delete

        Returns:
            True if there are at least n messages
        """
        if not self.orchestrator.session:
            return False

        history = self.orchestrator.session.get_history()
        return len(history) >= n

    def reroll_last_response(self, game_session: GameSession) -> Optional[str]:
        """
        Delete the last assistant message and return the user message to resend.

        Args:
            game_session: Current game session

        Returns:
            The user message to resend, or None if reroll not possible
        """
        if not self.can_reroll():
            logger.warning("Cannot reroll: last message is not from assistant")
            return None

        session = self.orchestrator.session
        history = session.get_history()

        # Find the last user message (should be second-to-last)
        user_message = None
        if len(history) >= 2 and history[-2].role == "user":
            user_message = history[-2].content

        # Delete last assistant message from Session
        logger.info("🔄 Rerolling: Removing last assistant message")
        session.history.pop()  # Remove last message

        # Delete last bubble from UI
        self.bubble_manager.bubble_labels.pop()  # Remove widget reference

        # Find and destroy the last bubble widget
        chat_widgets = self.bubble_manager.chat_frame.winfo_children()
        if chat_widgets:
            chat_widgets[-1].destroy()

        # Update database
        game_session.session_data = session.to_json()
        self.db_manager.update_session(game_session)

        logger.info("✅ Reroll prepared, returning user message for regeneration")
        return user_message

    def delete_last_n_messages(self, game_session: GameSession, n: int) -> bool:
        """
        Delete the last N messages from history and UI.

        Args:
            game_session: Current game session
            n: Number of messages to delete

        Returns:
            True if deletion succeeded
        """
        if not self.can_delete(n):
            logger.warning(
                f"Cannot delete {n} messages: not enough messages in history"
            )
            return False

        session = self.orchestrator.session

        logger.info(f"🗑️ Deleting last {n} messages")

        # Delete from Session history
        for _ in range(n):
            if session.history:
                session.history.pop()

        # Delete from UI
        for _ in range(n):
            if self.bubble_manager.bubble_labels:
                self.bubble_manager.bubble_labels.pop()

            chat_widgets = self.bubble_manager.chat_frame.winfo_children()
            if chat_widgets:
                chat_widgets[-1].destroy()

        # Update database
        game_session.session_data = session.to_json()
        self.db_manager.update_session(game_session)

        logger.info(f"✅ Deleted {n} messages")

        # Show confirmation in chat
        self.bubble_manager.add_message("system", f"🗑️ Deleted last {n} message(s)")

        return True

    def get_history_length(self) -> int:
        """Get current history length."""
        if not self.orchestrator.session:
            return 0
        return len(self.orchestrator.session.get_history())
