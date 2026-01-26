import logging
import os
import queue
import threading
import uuid
from typing import Callable

from app.core.react_turn_manager import ReActTurnManager
from app.core.vector_store import VectorStore
from app.database.db_manager import DBManager
from app.llm.gemini_connector import GeminiConnector
from app.llm.llm_connector import LLMConnector
from app.llm.openai_connector import OpenAIConnector
from app.models.game_session import GameSession
from app.models.session import Session
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self, bridge, db_path: str):
        self.bridge = bridge
        self.db_path = db_path

        # Use the Bridge's UI queue so all UI events flow through one place
        self.ui_queue: queue.Queue = bridge.ui_queue
        self.tool_event_callback: Callable[[str], None] | None = None
        self.logger = logger

        # Core Components
        self.llm_connector = self._get_llm_connector()
        self.tool_registry = ToolRegistry()
        self.vector_store = VectorStore()
        self.session: Session | None = None

        # Turn Manager
        self.turn_manager = ReActTurnManager(self)

        # Threading Control
        self.stop_event = threading.Event()
        self.active_turn_id: str | None = None

    def _get_llm_connector(self) -> LLMConnector:
        provider = os.environ.get("LLM_PROVIDER", "GEMINI").upper()
        if provider == "GEMINI":
            return GeminiConnector()
        elif provider == "OPENAI":
            return OpenAIConnector()
        else:
            raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")

    def stop_generation(self):
        """Signal the running turn to stop and ignore subsequent UI events."""
        self.logger.info("🛑 Stop signal received.")
        self.stop_event.set()

        # Invalidate current turn ID so late UI events are dropped
        self.active_turn_id = None
        self.bridge.set_active_turn(None)

    def plan_and_execute(self, session: GameSession):
        logger.debug("Starting plan_and_execute (non-blocking)")

        # 1. Cancel any running turn first to prevent race conditions
        if self.active_turn_id:
            self.stop_generation()

        user_input = self.bridge.get_input()

        if not user_input or not self.session:
            return

        # 2. Generate Turn ID
        self.active_turn_id = uuid.uuid4().hex
        self.bridge.set_active_turn(self.active_turn_id)

        # 3. Optimistic UI update (tagged with turn_id)
        self.session.add_message("user", user_input)
        self.ui_queue.put(
            {
                "type": "message_bubble",
                "role": "user",
                "content": user_input,
                "turn_id": self.active_turn_id,
            }
        )
        self.bridge.clear_input()

        session.session_data = self.session.to_json()

        # Reset stop flag before starting
        self.stop_event.clear()

        thread = threading.Thread(
            target=self._background_execute,
            args=(session, user_input, self.active_turn_id),
            daemon=True,
            name=f"Turn-{session.id}-{self.active_turn_id}",
        )
        thread.start()

    def _background_execute(
        self, game_session: GameSession, user_input: str, turn_id: str
    ):
        logger.debug(
            f"Executing _background_execute for session {game_session.id}, turn {turn_id}"
        )
        try:
            with DBManager(self.db_path) as thread_db_manager:
                self.turn_manager.execute_turn(game_session, thread_db_manager, turn_id)
        except Exception as e:
            logger.error(f"Turn failed: {e}", exc_info=True)
            self.ui_queue.put({"type": "error", "message": str(e), "turn_id": turn_id})
        finally:
            self.ui_queue.put({"type": "turn_complete", "turn_id": turn_id})

    def _update_game_in_thread(
        self,
        game_session: GameSession,
        db_manager: DBManager,
        final_session_state: Session,
    ):
        """Helper to update the game session in the database from a background thread."""
        if not game_session:
            return
        game_session.session_data = final_session_state.to_json()
        db_manager.sessions.update(game_session)
        self.session = final_session_state
        self.session.id = game_session.id

    # --- Session Management ---

    def load_game(self, session_id: int):
        with DBManager(self.db_path) as db_manager:
            game_session = db_manager.sessions.get_by_id(session_id)
        if game_session:
            self.session = Session.from_json(game_session.session_data)
            self.session.id = game_session.id

    # --- History Manipulation ---

    def reroll_last_turn(self, game_session: GameSession):
        """Deletes the last Assistant response and re-runs the turn with the previous User input."""
        if not self.session or not self.session.history:
            return

        history = self.session.history

        if history[-1].role != "assistant":
            self.ui_queue.put(
                {
                    "type": "error",
                    "message": "Cannot reroll: Last message was not from AI.",
                }
            )
            return

        history.pop()

        last_user_msg = ""
        if history and history[-1].role == "user":
            last_user_msg = history[-1].content

        self.session.session_data = self.session.to_json()
        game_session.session_data = self.session.to_json()

        with DBManager(self.db_path) as db:
            db.sessions.update(game_session)

        self.ui_queue.put({"type": "history_changed"})

        # Reset stop flag and set new turn ID
        self.stop_event.clear()
        self.active_turn_id = uuid.uuid4().hex
        self.bridge.set_active_turn(self.active_turn_id)

        if last_user_msg:
            thread = threading.Thread(
                target=self._background_execute,
                args=(game_session, last_user_msg, self.active_turn_id),
                daemon=True,
            )
            thread.start()

    def undo_last_turn(self, game_session: GameSession):
        """Deletes the last Assistant response AND the last User message."""
        if not self.session or not self.session.history:
            return

        history = self.session.history

        if history and history[-1].role == "assistant":
            history.pop()

        if history and history[-1].role == "user":
            history.pop()

        game_session.session_data = self.session.to_json()
        with DBManager(self.db_path) as db:
            db.sessions.update(game_session)

        self.ui_queue.put({"type": "history_changed"})
