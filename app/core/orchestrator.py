import os
import json as _json
import logging
from typing import Callable
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
from app.core.llm.prompts import PLAN_TEMPLATE, NARRATIVE_TEMPLATE, CHOICE_GENERATION_TEMPLATE
from app.core.llm.planner_service import PlannerService
from app.core.llm.narrator_service import NarratorService
from app.core.llm.choices_service import ChoicesService
from app.core.llm.auditor_service import AuditorService
from app.core.tools.executor import ToolExecutor
from app.core.metadata.turn_metadata_service import TurnMetadataService
from app.core.memory.memory_intents_service import MemoryIntentsService

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

MAX_HISTORY_MESSAGES = 20
TOOL_BUDGET = 10

class Orchestrator:
    def __init__(self, view: MainView, db_manager):
        self.view = view
        self.db_manager = db_manager
        self.tool_event_callback: Callable[[str], None] | None = None
        self.llm_connector = self._get_llm_connector()
        self.tool_registry = ToolRegistry()
        self.vector_store = VectorStore()
        self.session: Session | None = None

        # Compose services
        state_builder = StateContextBuilder(self.tool_registry, self.db_manager, logger)
        mem_retriever = MemoryRetriever(self.db_manager, self.vector_store, logger)
        self.turnmeta = TurnMetadataService(self.db_manager, self.vector_store)
        world_info = WorldInfoService(self.db_manager, self.vector_store, logger)
        self.context_builder = ContextBuilder(
            self.db_manager, self.vector_store,
            state_builder, mem_retriever, self.turnmeta, world_info, logger
        )
        self.planner = PlannerService(self.llm_connector)
        self.narrator = NarratorService(self.llm_connector)
        self.choices = ChoicesService(self.llm_connector)
        self.executor = ToolExecutor(self.tool_registry, self.db_manager, self.vector_store, ui=self.view, logger=logger)
        self.auditor = AuditorService(self.llm_connector, self.tool_registry, self.db_manager, self.vector_store, logger)
        self.mem_intents = MemoryIntentsService(self.tool_registry, self.db_manager, self.vector_store, logger)

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
        logger.debug("Starting plan_and_execute")
        user_input = self.view.get_input()
        if not user_input or not self.session:
            logger.debug("No user input or session found, returning.")
            return

        # Append user message to history and UI
        self.session.add_message("user", user_input)
        self.view.add_message_bubble("user", user_input)
        self.view.clear_input()

        # Step 1: Plan
        chat_history = self.context_builder.get_truncated_history(self.session, MAX_HISTORY_MESSAGES)
        base_plan_template = PLAN_TEMPLATE.format(
            identity=chat_history[0].content if chat_history else "",
            tool_schemas=_json.dumps(self.tool_registry.get_all_schemas(), indent=2),
            tool_budget=TOOL_BUDGET,
        )
        system_prompt_plan = self.context_builder.assemble(base_plan_template, session, chat_history)
        plan = self.planner.plan(system_prompt_plan, chat_history)
        if not plan:
            logger.error("LLM returned no structured response for TurnPlan.")
            self.view.add_message_bubble("system", "Error: AI failed to generate a valid plan.")
            return
        self.view.add_thought_bubble(plan.thought)

        # Step 2: Execute tools
        tool_results, memory_tool_used = self.executor.execute(plan.tool_calls, session, TOOL_BUDGET, current_game_time=getattr(session, "game_time", None))
        if memory_tool_used and hasattr(self.view, 'memory_inspector'):
            self.view.after(100, self.view.memory_inspector.refresh_memories)

        # Step 2.5: Audit
        audit_history = self.context_builder.get_truncated_history(self.session, MAX_HISTORY_MESSAGES)
        audit = self.auditor.audit(audit_history, tool_results)
        if audit and not audit.ok:
            self.auditor.apply_remediations(audit, session)

        # Step 3: Narrative
        chat_history = self.context_builder.get_truncated_history(self.session, MAX_HISTORY_MESSAGES)
        base_narr_template = NARRATIVE_TEMPLATE.format(
            identity=chat_history[0].content if chat_history else "",
            planner_thought=plan.thought,
            tool_results=str(tool_results)
        )
        system_prompt_narr = self.context_builder.assemble(base_narr_template, session, chat_history)
        narrative = self.narrator.write_step(system_prompt_narr, chat_history)
        if not narrative:
            logger.error("LLM returned no structured response for NarrativeStep.")
            self.view.add_message_bubble("system", "Error: AI failed to generate a valid narrative.")
            return

        self.view.add_message_bubble("assistant", narrative.narrative)
        self.session.add_message("assistant", narrative.narrative)

        # Step 3.5: Turn metadata
        if session.id:
            round_number = len(self.session.get_history()) // 2
            self.turnmeta.persist(
                session_id=session.id,
                prompt_id=session.prompt_id,
                round_number=round_number,
                summary=narrative.turn_summary,
                tags=narrative.turn_tags,
                importance=narrative.turn_importance
            )
            logger.debug(f"Stored metadata for turn {round_number}")

        # Step 4: Apply patches and memory intents
        if narrative.proposed_patches:
            for patch in narrative.proposed_patches:
                try:
                    args = {"entity_type": patch.entity_type, "key": patch.key, "patch": [op.model_dump() for op in patch.ops]}
                    result = self.tool_registry.execute_tool("state.apply_patch", args, context={"session_id": session.id, "db_manager": self.db_manager})
                    if self.tool_event_callback:
                        self.tool_event_callback(f"state.apply_patch ✓ -> {result}")
                except Exception as e:
                    logger.error(f"Patch error: {e}")

        self.mem_intents.apply(narrative.memory_intents, session, tool_event_callback=self.tool_event_callback)

        # Step 5: Action choices
        try:
            choice_template = CHOICE_GENERATION_TEMPLATE.format(narrative=narrative.narrative)
            system_prompt_choices = self.context_builder.assemble(choice_template, session, chat_history)
            choices = self.choices.generate(system_prompt_choices, chat_history)
            if choices and choices.choices:
                self.view.display_action_choices(choices.choices)
            else:
                logger.warning("Failed to generate action choices")
        except Exception as e:
            logger.error(f"Error generating action choices: {e}", exc_info=True)

        # Persist session
        self.update_game(session)

    def run(self):
        self.view.mainloop()

    def new_session(self, system_prompt: str):
        self.session = Session("default_session", system_prompt=system_prompt)

    def save_game(self, name: str, prompt_id: int):
        if not self.session:
            logger.error("Cannot save game: no active session")
            return
        session_data = self.session.to_json()
        game_session = self.db_manager.save_session(name, session_data, prompt_id)
        self.session.id = game_session.id
        self.view.session_name_label.configure(text=name)

    def load_game(self, session_id: int):
        game_session = self.db_manager.load_session(session_id)
        if game_session:
            self.session = Session.from_json(game_session.session_data)
            self.session.id = game_session.id

    def update_game(self, session: GameSession):
        if not self.session:
            return
        session.session_data = self.session.to_json()
        self.db_manager.update_session(session)
