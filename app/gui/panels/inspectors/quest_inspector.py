# File: app/gui/panels/inspectors/quest_inspector.py
# --- NEW FILE ---

import customtkinter as ctk
import logging
from typing import Callable
from app.gui.styles import Theme
from app.tools.schemas import StateQuery
from .inspector_utils import create_quest_card, display_message_state

logger = logging.getLogger(__name__)

class QuestPanelBuilder:
    """Builds the static UI for the Quest Inspector."""
    @staticmethod
    def build(parent: ctk.CTkFrame, refresh_callback: Callable) -> dict:
        scroll_frame = ctk.CTkScrollableFrame(
            parent, fg_color=Theme.colors.bg_secondary
        )
        scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

        ctk.CTkButton(parent, text="🔄 Refresh", command=refresh_callback, height=30).pack(
            fill="x", padx=5, pady=5
        )
        return {"scroll_frame": scroll_frame}

class QuestInspectorView(ctk.CTkFrame):
    """Display active quests."""

    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.db_manager = db_manager
        self.orchestrator = None
        self.quests_data = {}

        self.widgets = QuestPanelBuilder.build(self, refresh_callback=self.refresh)

    def refresh(self):
        """Query all quests."""
        if not self.orchestrator or not self.orchestrator.session:
            display_message_state(self.widgets["scroll_frame"], "No session loaded.", is_error=True)
            return

        session_id = self.orchestrator.session.id
        try:
            from app.tools.registry import ToolRegistry
            registry = ToolRegistry()
            context = {"session_id": session_id, "db_manager": self.db_manager}
            query = StateQuery(entity_type="quest", key="*", json_path=".")
            result = registry.execute(query, context=context)
            self.quests_data = result.get("value", {})
            self._render_quests()
        except Exception as e:
            logger.error(f"Exception in refresh: {e}", exc_info=True)
            display_message_state(self.widgets["scroll_frame"], f"Error: {e}", is_error=True)

    def _render_quests(self):
        """Render quest cards."""
        scroll_frame = self.widgets["scroll_frame"]
        for widget in scroll_frame.winfo_children():
            widget.destroy()

        if not self.quests_data or not isinstance(self.quests_data, dict):
            display_message_state(scroll_frame, "No active quests.")
            return

        for quest_id, quest in self.quests_data.items():
            create_quest_card(scroll_frame, quest_id, quest)
