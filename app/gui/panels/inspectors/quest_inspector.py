import customtkinter as ctk
import logging
from typing import Callable
from app.gui.styles import Theme
from app.tools.builtin._state_storage import get_versions, get_all_of_type
from .inspector_utils import create_quest_card, display_message_state

logger = logging.getLogger(__name__)


class QuestPanelBuilder:
    @staticmethod
    def build(parent: ctk.CTkFrame, refresh_callback: Callable) -> dict:
        scroll_frame = ctk.CTkScrollableFrame(
            parent, fg_color=Theme.colors.bg_secondary
        )
        scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        ctk.CTkButton(parent, text="Refresh", command=refresh_callback, height=30).pack(
            fill="x", padx=5, pady=5
        )
        return {"scroll_frame": scroll_frame}


class QuestInspectorView(ctk.CTkFrame):
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.db_manager = db_manager
        self.orchestrator = None
        self.quests_data = {}

        # Cache: sum of all quest versions to detect any change
        self.last_cache_signature = -1

        self.widgets = QuestPanelBuilder.build(self, refresh_callback=self.refresh)

    def refresh(self):
        if not self.orchestrator or not self.orchestrator.session:
            display_message_state(
                self.widgets["scroll_frame"], "No session loaded.", is_error=True
            )
            return

        session_id = self.orchestrator.session.id

        # 1. Check Versions
        try:
            versions = get_versions(session_id, self.db_manager, "quest")
        except Exception as e:
            # logs a warning
            logger.warning(f"Error fetching versions: {e}")
            return

        # Simple signature: sum of versions. If any quest updates, this changes.
        # (Technically collision possible if one +1 and one -1, but versions only increment)
        current_sig = sum(versions.values())

        if current_sig > self.last_cache_signature:
            self._fetch_and_render(session_id)
            self.last_cache_signature = current_sig

    def _fetch_and_render(self, session_id):
        self.quests_data = get_all_of_type(session_id, self.db_manager, "quest")
        self._render_quests()

    def _render_quests(self):
        scroll_frame = self.widgets["scroll_frame"]
        for widget in scroll_frame.winfo_children():
            widget.destroy()

        if not self.quests_data:
            display_message_state(scroll_frame, "No active quests.")
            return

        for quest_id, quest in self.quests_data.items():
            create_quest_card(scroll_frame, quest_id, quest)
