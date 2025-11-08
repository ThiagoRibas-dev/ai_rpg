import os
import logging
import queue
import threading
from typing import Callable, List, Dict, Any, Type
from pydantic import BaseModel
from app.database.db_manager import DBManager
from app.gui.main_view import MainView
from app.models.session import Session
from app.models.game_session import GameSession
from app.llm.llm_connector import LLMConnector
from app.llm.gemini_connector import GeminiConnector
from app.llm.openai_connector import OpenAIConnector
from app.tools.registry import ToolRegistry
from app.core.vector_store import VectorStore
from app.core.context.state_context import StateContextBuilder
from app.core.context.memory_retriever import MemoryRetriever
from app.core.context.world_info_service import WorldInfoService
from app.core.context.context_builder import ContextBuilder
from app.core.llm.prompts import (
    PLAN_TEMPLATE,
    NARRATIVE_TEMPLATE,
    CHOICE_GENERATION_TEMPLATE,
    SETUP_RESPONSE_TEMPLATE,
)
from app.core.llm.planner_service import PlannerService
from app.core.llm.narrator_service import NarratorService
from app.core.llm.choices_service import ChoicesService
from app.core.llm.auditor_service import AuditorService
from app.core.tools.executor import ToolExecutor
from app.core.metadata.turn_metadata_service import TurnMetadataService
from app.core.memory.memory_intents_service import MemoryIntentsService
from app.tools.schemas import StateApplyPatch, Patch

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

MAX_HISTORY_MESSAGES = 20
TOOL_BUDGET = 10


class Orchestrator:
    def __init__(self, view: MainView, db_path: str):  # Changed to db_path
        self.view = view
        self.db_path = db_path  # Store path, not manager
        self.ui_queue = queue.Queue()  # Initialize UI queue
        self.tool_event_callback: Callable[[str], None] | None = None
        self.llm_connector = self._get_llm_connector()
        self.tool_registry = ToolRegistry()
        self.vector_store = VectorStore()
        self.session: Session | None = None
        # Services that don't need DB connection in __init__
        self.planner = PlannerService(self.llm_connector)
        self.narrator = NarratorService(self.llm_connector)
        self.choices = ChoicesService(self.llm_connector)
        self.auditor = AuditorService(
            self.llm_connector, self.tool_registry, None, self.vector_store, logger
        )  # DBManager will be passed in _background_execute
        self.mem_intents = MemoryIntentsService(
            self.tool_registry, None, self.vector_store, logger
        )  # DBManager will be passed in _background_execute
        # Wire GUI
        self.view.orchestrator = self
        if hasattr(self.view, "memory_inspector"):
            self.view.memory_inspector.orchestrator = self

    def _get_llm_connector(self) -> LLMConnector:
        provider = os.environ.get("LLM_PROVIDER", "GEMINI").upper()
        if provider == "GEMINI":
            return GeminiConnector()
        elif provider == "OPENAI":
            return OpenAIConnector()
        else:
            raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")

    def plan_and_execute(self, session: GameSession):
        logger.debug("Starting plan_and_execute (non-blocking)")
        user_input = self.view.get_input()
        if not user_input or not self.session:
            logger.debug("No user input or session found, returning.")
            return
        # Append user message to history and UI
        # self.session is the in-memory Session object
        if self.session is None:  # Mypy guard
            logger.error("No active session to add message to.")
            self.ui_queue.put({"type": "error", "message": "No active session."})
            self.ui_queue.put({"type": "turn_complete"})
            return
        self.session.add_message("user", user_input)
        self.ui_queue.put(
            {"type": "message_bubble", "role": "user", "content": user_input}
        )
        self.view.clear_input()
        # Update the GameSession object's session_data with the latest in-memory Session state
        session.session_data = self.session.to_json()
        # Start background thread, passing the GameSession object directly
        thread = threading.Thread(
            target=self._background_execute,
            args=(session, user_input),  # Pass the GameSession object directly
            daemon=True,
            name=f"Turn-{session.id}",
        )
        thread.start()

    def _background_execute(self, game_session: GameSession, user_input: str):
        logger.debug(f"Executing _background_execute for session {game_session.id}")
        try:
            # Thread-local DB connection
            with DBManager(self.db_path) as thread_db_manager:
                # Recreate services with thread-local DBManager
                state_builder = StateContextBuilder(
                    self.tool_registry, thread_db_manager, logger
                )
                mem_retriever = MemoryRetriever(
                    thread_db_manager, self.vector_store, logger
                )
                turnmeta = TurnMetadataService(thread_db_manager, self.vector_store)
                world_info = WorldInfoService(
                    thread_db_manager, self.vector_store, logger
                )
                context_builder = ContextBuilder(
                    thread_db_manager,
                    self.vector_store,
                    state_builder,
                    mem_retriever,
                    turnmeta,
                    world_info,
                    logger,
                )
                executor = ToolExecutor(
                    self.tool_registry,
                    thread_db_manager,
                    self.vector_store,
                    ui_queue=self.ui_queue,
                    logger=logger,
                )
                auditor = AuditorService(
                    self.llm_connector,
                    self.tool_registry,
                    thread_db_manager,
                    self.vector_store,
                    logger,
                )
                mem_intents = MemoryIntentsService(
                    self.tool_registry, thread_db_manager, self.vector_store, logger
                )
                # Determine game mode and available tools
                current_game_mode = game_session.game_mode
                available_tool_models: List[Type[BaseModel]]
                available_tool_schemas_json: List[Dict[str, Any]]
                if current_game_mode == "SETUP":
                    setup_tool_names = ["schema.define_property", "schema.finalize"]
                    available_tool_models = self.tool_registry.get_tool_models(
                        setup_tool_names
                    )
                    available_tool_schemas_json = [
                        s
                        for s in self.tool_registry.get_all_schemas()
                        if s["name"] in setup_tool_names
                    ]
                    logger.debug(f"SETUP mode: Available tools: {setup_tool_names}")
                else:  # GAMEPLAY mode
                    available_tool_models = self.tool_registry.get_all_tool_types()
                    available_tool_schemas_json = self.tool_registry.get_all_schemas()
                    logger.debug(
                        f"GAMEPLAY mode: {len(available_tool_models)} tools available."
                    )
                # ===== BUILD STATIC SYSTEM INSTRUCTION =====
                static_instruction = context_builder.build_static_system_instruction(
                    game_session, available_tool_schemas_json
                )
                # ===== BUILD CHAT HISTORY (ONCE, before all phases) =====
                session_in_thread = Session.from_json(game_session.session_data)
                session_in_thread.id = game_session.id
                chat_history = context_builder.get_truncated_history(
                    session_in_thread, MAX_HISTORY_MESSAGES
                )
                # ===== BUILD DYNAMIC CONTEXT =====
                dynamic_context = context_builder.build_dynamic_context(
                    game_session, chat_history
                )
                # ===== STEP 1: PLAN =====
                if current_game_mode == "SETUP":
                    phase_template = context_builder.get_session_zero_prompt_template()
                else:
                    phase_template = PLAN_TEMPLATE.format(tool_budget=TOOL_BUDGET)
                plan = self.planner.plan(
                    system_instruction=static_instruction,
                    phase_template=phase_template,
                    dynamic_context=dynamic_context,
                    chat_history=chat_history,
                    available_tool_models=available_tool_models,
                )
                if not plan:
                    logger.error("LLM returned no structured response for TurnPlan.")
                    self.ui_queue.put(
                        {
                            "type": "error",
                            "message": "AI failed to generate a valid plan.",
                        }
                    )
                    return
                self.ui_queue.put({"type": "thought_bubble", "content": plan.thought})
                # Add validation check
                if plan.tool_calls:
                    logger.debug(f"Plan contains {len(plan.tool_calls)} tool calls:")
                    for i, call in enumerate(plan.tool_calls):
                        logger.debug(f"  {i}: {type(call).__name__}")
                # ===== STEP 2: EXECUTE TOOLS =====
                tool_results, memory_tool_used = executor.execute(
                    plan.tool_calls,
                    game_session,
                    TOOL_BUDGET,
                    current_game_time=getattr(game_session, "game_time", None),
                )
                if memory_tool_used and hasattr(self.view, "memory_inspector"):
                    self.ui_queue.put({"type": "refresh_memory_inspector"})
                # Check for schema.finalize tool call and update game mode
                for result in tool_results:
                    if result.get("tool_name") == "schema.finalize" and result.get(
                        "result", {}
                    ).get("setup_complete"):
                        game_session.game_mode = "GAMEPLAY"
                        # Invalidate cache since mode changed
                        if hasattr(game_session, "_cached_instruction"):
                            delattr(game_session, "_cached_instruction")
                        # Notify UI of mode change
                        self.ui_queue.put(
                            {"type": "update_game_mode", "new_mode": "GAMEPLAY"}
                        )
                        self.ui_queue.put(
                            {
                                "type": "message_bubble",
                                "role": "system",
                                "content": "✅ Session Zero complete! Game starting...",
                            }
                        )
                        logger.info(
                            "Session Zero finalized. Transitioning to GAMEPLAY mode."
                        )
                        self._update_game_in_thread(
                            game_session, thread_db_manager, session_in_thread
                        )
                        return
                # ===== STEP 2.5: AUDIT (only in GAMEPLAY mode) =====
                if current_game_mode == "GAMEPLAY":
                    audit_history = context_builder.get_truncated_history(
                        session_in_thread, MAX_HISTORY_MESSAGES
                    )
                    audit = auditor.audit(audit_history, tool_results)
                    if audit and not audit.ok:
                        auditor.apply_remediations(audit, game_session)
                # ===== STEP 3: NARRATIVE/RESPONSE (only in GAMEPLAY mode, or if setup tools didn't finalize) =====
                if current_game_mode == "GAMEPLAY" or not any(
                    r.get("tool_name") == "schema.finalize" for r in tool_results
                ):
                    # Rebuild dynamic context (state may have changed after tools)
                    dynamic_context = context_builder.build_dynamic_context(
                        game_session, chat_history
                    )
                    # ✅ Choose appropriate template based on game mode
                    if current_game_mode == "SETUP":
                        phase_template = SETUP_RESPONSE_TEMPLATE
                    else:  # GAMEPLAY
                        phase_template = NARRATIVE_TEMPLATE
                    narrative = self.narrator.write_step(
                        system_instruction=static_instruction,
                        phase_template=phase_template,
                        dynamic_context=dynamic_context,
                        plan_thought=plan.thought,
                        tool_results=str(tool_results),
                        chat_history=chat_history,
                    )
                    if not narrative:
                        logger.error(
                            "LLM returned no structured response for NarrativeStep."
                        )
                        self.ui_queue.put(
                            {
                                "type": "error",
                                "message": "AI failed to generate a valid narrative.",
                            }
                        )
                        return
                    self.ui_queue.put(
                        {
                            "type": "message_bubble",
                            "role": "assistant",
                            "content": narrative.response,
                        }
                    )
                    # ===== STEP 3.5: Turn metadata =====
                    # ✅ Only store turn metadata in GAMEPLAY mode
                    if current_game_mode == "GAMEPLAY" and game_session.id:
                        round_number = len(session_in_thread.get_history()) // 2 + 1
                        turnmeta.persist(
                            session_id=game_session.id,
                            prompt_id=game_session.prompt_id,
                            round_number=round_number,
                            summary=narrative.turn_summary,
                            tags=narrative.turn_tags,
                            importance=narrative.turn_importance,
                        )
                        logger.debug(f"Stored metadata for turn {round_number}")
                    # ===== STEP 4: Apply patches and memory intents =====
                    if narrative.proposed_patches:
                        for patch in narrative.proposed_patches:
                            try:
                                patch_call = StateApplyPatch(
                                    entity_type=patch.entity_type,
                                    key=patch.key,
                                    patch=[
                                        Patch(**op.model_dump()) for op in patch.ops
                                    ],
                                )
                                result = self.tool_registry.execute(
                                    patch_call,
                                    context={
                                        "session_id": game_session.id,
                                        "db_manager": thread_db_manager,
                                    },
                                )
                                if self.tool_event_callback:
                                    self.ui_queue.put(
                                        {
                                            "type": "tool_event",
                                            "message": f"state.apply_patch ✓ → {result}",
                                        }
                                    )
                            except Exception as e:
                                logger.error(f"Patch error: {e}")
                                self.ui_queue.put(
                                    {"type": "error", "message": f"Patch error: {e}"}
                                )
                    mem_intents.apply(
                        narrative.memory_intents,
                        session_in_thread,
                        tool_event_callback=self.tool_event_callback,
                    )
                    # ===== STEP 5: Action choices =====
                    # ✅ Only generate choices in GAMEPLAY mode
                    if current_game_mode == "GAMEPLAY":
                        try:
                            phase_template = CHOICE_GENERATION_TEMPLATE
                            choices = self.choices.generate(
                                system_instruction=static_instruction,
                                phase_template=phase_template,
                                narrative_text=narrative.response,
                                chat_history=chat_history,
                            )
                            if choices and choices.choices:
                                self.ui_queue.put(
                                    {"type": "choices", "choices": choices.choices}
                                )
                            else:
                                logger.warning("Failed to generate action choices")
                        except Exception as e:
                            logger.error(
                                f"Error generating action choices: {e}", exc_info=True
                            )
                            self.ui_queue.put(
                                {
                                    "type": "error",
                                    "message": f"Error generating action choices: {e}",
                                }
                            )
                    # ===== NOW add narrative to chat history (all phases complete) =====
                    session_in_thread.add_message("assistant", narrative.response)
                    logger.debug(
                        f"DEBUG: Added AI response to chat history: {narrative.response}"
                    )
                # Persist session, passing the final state from the thread
                self._update_game_in_thread(
                    game_session, thread_db_manager, session_in_thread
                )
        except Exception as e:
            logger.error(f"Turn failed: {e}", exc_info=True)
            self.ui_queue.put({"type": "error", "message": str(e)})
        finally:
            self.ui_queue.put({"type": "turn_complete"})

    def _update_game_in_thread(
        self,
        game_session: GameSession,
        db_manager: DBManager,
        final_session_state: Session,
    ):
        """
        Helper to update the game session in the database from a background thread.
        This now requires the final state of the session from the thread to ensure correctness.
        """
        if not game_session:
            return
        # The source of truth is the session object from the background thread
        game_session.session_data = final_session_state.to_json()
        db_manager.update_session(game_session)
        # Update the main orchestrator's session object as well, so the UI can reflect history
        self.session = final_session_state
        self.session.id = game_session.id  # Ensure ID is set

    def run(self):
        self.view.mainloop()

    def new_session(self, system_prompt: str):
        self.session = Session("default_session", system_prompt=system_prompt)

    def save_game(self, name: str, prompt_id: int):
        if self.session is None:  # Mypy guard
            logger.error("Cannot save game: no active session")
            return
        session_data = self.session.to_json()
        with DBManager(self.db_path) as db_manager:  # Use thread-local DB
            game_session = db_manager.save_session(name, session_data, prompt_id)
        self.session.id = game_session.id
        self.view.session_name_label.configure(text=name)

    def load_game(self, session_id: int):
        with DBManager(self.db_path) as db_manager:  # Use thread-local DB
            game_session = db_manager.load_session(session_id)
        if game_session:
            self.session = Session.from_json(game_session.session_data)
            self.session.id = game_session.id

    def update_game(self, session: GameSession):
        if self.session is None:  # Mypy guard
            return
        session.session_data = self.session.to_json()
        with DBManager(self.db_path) as db_manager:  # Use thread-local DB
            db_manager.update_session(session)
