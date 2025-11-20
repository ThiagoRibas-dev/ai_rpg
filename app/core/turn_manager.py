import logging

from app.context.context_builder import ContextBuilder
from app.context.memory_retriever import MemoryRetriever
from app.context.state_context import StateContextBuilder
from app.core.metadata.turn_metadata_service import TurnMetadataService
from app.core.simulation_service import SimulationService
from app.database.db_manager import DBManager
from app.llm.auditor_service import AuditorService
from app.llm.choices_service import ChoicesService
from app.llm.narrator_service import NarratorService
from app.llm.planner_service import PlannerService
from app.llm.schemas import SceneSummary
from app.models.game_session import GameSession
from app.models.session import Session
from app.prompts.builder import build_ruleset_summary
from app.prompts.templates import (
    CHOICE_GENERATION_TEMPLATE,
    GAMEPLAY_PLAN_TEMPLATE,
    NARRATIVE_TEMPLATE,
    SETUP_PLAN_TEMPLATE,
    SCENE_SUMMARIZATION_TEMPLATE,
    TOOL_SELECTION_PER_STEP_TEMPLATE,
    SETUP_RESPONSE_TEMPLATE,
)
from app.setup.setup_manifest import SetupManifest
from app.tools.executor import ToolExecutor
from app.tools.schemas import (
    CharacterUpdate,
    Deliberate,
    SchemaQuery,
)

MAX_HISTORY_MESSAGES = 50
TOOL_BUDGET = 20
 
logger = logging.getLogger(__name__)


class TurnManager:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.logger = orchestrator.logger
        self.llm_connector = orchestrator.llm_connector
        self.tool_registry = orchestrator.tool_registry
        self.vector_store = orchestrator.vector_store
        self.ui_queue = orchestrator.ui_queue
        # Services that don't need a DB manager at init time
        self.planner = PlannerService(self.llm_connector)
        self.narrator = NarratorService(self.llm_connector)
        self.choices = ChoicesService(self.llm_connector)

    def execute_turn(self, game_session: GameSession, thread_db_manager: DBManager):
        """The main game loop for a single turn. Replaces Orchestrator._background_execute."""
        session_in_thread = Session.from_json(game_session.session_data)
        session_in_thread.id = game_session.id

        # Recreate services with thread-local DBManager
        state_builder = StateContextBuilder(
            self.tool_registry, thread_db_manager, self.logger
        )
        mem_retriever = MemoryRetriever(
            thread_db_manager, self.vector_store, self.logger
        )

        # --- FIX: Re-instantiate the TurnMetadataService here ---
        turnmeta = TurnMetadataService(thread_db_manager, self.vector_store)

        # --- NEW: Instantiate SimulationService ---
        simulation_service = SimulationService(self.llm_connector, self.logger)
        context_builder = ContextBuilder(
            thread_db_manager,
            self.vector_store,
            state_builder,
            mem_retriever,
            simulation_service,  # This is still correct
            self.logger,
        )
        executor = ToolExecutor(
            self.tool_registry,
            thread_db_manager,
            self.vector_store,
            ui_queue=self.ui_queue,
            logger=self.logger,
        )
        auditor = AuditorService(
            self.llm_connector,
            self.tool_registry,
            thread_db_manager,
            self.vector_store,
            self.logger,
        )

        # Initialize manifest manager early for tool selection logic
        manifest_mgr = SetupManifest(thread_db_manager)

        # Determine game mode and available tools
        current_game_mode = game_session.game_mode
        if current_game_mode == "SETUP":
            # Base tools available in all Setup states
            setup_tool_names = [
                CharacterUpdate.model_fields["name"].default,
                Deliberate.model_fields["name"].default,
                SchemaQuery.model_fields["name"].default,
            ]

            self.logger.debug(f"SETUP MODE TOOLS: {setup_tool_names}")
        else:  # GAMEPLAY mode
            # If not in SETUP, all tools are available except the setup-specific ones.
            setup_tool_names = self.tool_registry.get_all_tool_names()

        # ===== BUILD STATIC SYSTEM INSTRUCTION =====
        # manifest_mgr already initialized above
        manifest = manifest_mgr.get_manifest(game_session.id)

        ruleset_text = ""
        if manifest.get("ruleset_id") and thread_db_manager.rulesets:
            ruleset = thread_db_manager.rulesets.get_by_id(manifest["ruleset_id"])
            if ruleset:
                ruleset_text = build_ruleset_summary(ruleset)

        # Pass ruleset summary to context builder
        static_instruction = context_builder.build_static_system_instruction(
            game_session, ruleset_text
        )

        # ===== BUILD CHAT HISTORY (ONCE, before all phases) =====
        chat_history = context_builder.get_truncated_history(
            session_in_thread, MAX_HISTORY_MESSAGES
        )

        # ===== BUILD DYNAMIC CONTEXT =====
        dynamic_context = context_builder.build_dynamic_context(
            game_session, chat_history
        )

        # ===== STEP 1: PLAN (2-PHASE PROCESS for ALL modes) =====
        # --- Signal the start of the turn to the UI to show the loading indicator immediately ---
        self.ui_queue.put({"type": "planning_started", "content": "Planning..."})

        # Phase 1: Create Plan (Analysis + Strategy)
        if current_game_mode == "SETUP":
            # Check confirmation status to inject into the dynamic prompt
            is_pending = manifest_mgr.is_pending_confirmation(game_session.id)
            status_str = (
                "WAITING FOR CONFIRMATION (Summary Presented)"
                if is_pending
                else "IN PROGRESS (Defining Game)"
            )

            # Inject status into the template placeholder
            plan_template = SETUP_PLAN_TEMPLATE.format(setup_status=status_str)
        else:
            plan_template = GAMEPLAY_PLAN_TEMPLATE

        turn_plan = self.planner.create_plan(
            system_instruction=static_instruction,
            phase_template=plan_template,
            dynamic_context=dynamic_context,
            chat_history=chat_history,
        )
        if not turn_plan:
            self.logger.error("LLM returned no structured response for TurnPlan.")
            self.ui_queue.put(
                {"type": "error", "message": "AI failed to create a plan."}
            )
            return
        analysis_text = turn_plan.analysis
        plan_steps = turn_plan.plan_steps

        if not plan_steps:
            self.logger.warning("LLM returned an empty list of plan steps.")

        # --- Iterative Tool Selection ---
        # Instead of one big call, we loop through each plan step and select tools individually.
        # This is more reliable for models that are reluctant to call multiple tools.
        all_tool_calls = []
        if plan_steps:
            self.logger.debug(
                f"Starting iterative tool selection for {len(plan_steps)} steps."
            )
            for i, step in enumerate(plan_steps):
                self.logger.debug(f"  -> Selecting tool for step {i + 1}: '{step}'")
                # Use the new per-step planner method
                step_tool_calls = self.planner.select_tools_for_step(
                    system_instruction=static_instruction,
                    phase_template=TOOL_SELECTION_PER_STEP_TEMPLATE,
                    analysis=analysis_text,
                    plan_step=step,
                    chat_history=chat_history,
                    tool_registry=self.tool_registry,
                    available_tool_names=setup_tool_names,
                )
                if step_tool_calls:
                    self.logger.debug(
                        f"  <- Selected {len(step_tool_calls)} tool(s) for step {i + 1}."
                    )
                    all_tool_calls.extend(step_tool_calls)

        tool_calls = all_tool_calls

        # ===== Construct plan summary for UI and Narration =====
        plan_steps_text = "\n - ".join(plan_steps)
        plan_steps_text = f" - {plan_steps_text}"

        tools_called = (
            ", ".join([tool.name for tool in tool_calls]) if tool_calls else ""
        )
        tools_called = f"""Tools Called: {tools_called}""" if tools_called else ""

        plan_summary = f"""{analysis_text}\n\n{plan_steps_text}\n\n{tools_called}"""

        self.ui_queue.put({"type": "thought_bubble", "content": plan_summary})

        # ===== STEP 2: EXECUTE TOOLS =====
        tool_results, memory_tool_used = executor.execute(
            tool_calls,
            game_session,
            manifest,
            TOOL_BUDGET,
            current_game_time=getattr(game_session, "game_time", None),
        )

        # Check for Scene Change Trigger
        scene_changed = False

        for result in tool_results:
            # Phase 4: Detect Location Change
            if result.get("ui_event") == "location_change":
                scene_changed = True

        # ===== STEP 2.5: AUDIT (only in GAMEPLAY mode) =====
        if current_game_mode == "GAMEPLAY":
            audit_history = context_builder.get_truncated_history(
                session_in_thread, MAX_HISTORY_MESSAGES
            )
            audit = auditor.audit(audit_history, tool_results)
            if audit and not audit.ok:
                auditor.apply_remediations(audit, game_session)

        # ===== STEP 3: NARRATIVE/RESPONSE =====
        dynamic_context = context_builder.build_dynamic_context(
            game_session, chat_history
        )
        phase_template = (
            SETUP_RESPONSE_TEMPLATE
            if current_game_mode == "SETUP"
            else NARRATIVE_TEMPLATE
        )

        tool_result_list = "\n".join([str(result) for result in tool_results])

        narrative = self.narrator.write_step(
            system_instruction=static_instruction,
            phase_template=phase_template,
            dynamic_context=dynamic_context,
            plan_thought=plan_summary,
            tool_results=tool_result_list,
            chat_history=chat_history,
        )
        if not narrative:
            self.logger.error("LLM returned no structured response for NarrativeStep.")
            self.ui_queue.put(
                {"type": "error", "message": "AI failed to generate a valid narrative."}
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

            # Phase 4: Trigger Scene Summarization if location changed
            if scene_changed:
                self._summarize_previous_scene(
                    game_session, thread_db_manager, round_number
                )

        # ===== STEP 4: Apply patches (DEPRECATED/REMOVED) =====
        # Phase 1 Refactor: We no longer allow the LLM to output raw JSON patches via Narrative.
        # Any state change must happen via Tools in Step 2.
        if narrative.proposed_patches:
            self.logger.warning(
                "Narrative contained proposed_patches, but patch application is disabled in v15 engine."
            )

        # ===== STEP 5: Action choices =====
        if current_game_mode == "GAMEPLAY":
            try:
                choices = self.choices.generate(
                    system_instruction=static_instruction,
                    phase_template=CHOICE_GENERATION_TEMPLATE,
                    narrative_text=narrative.response,
                    chat_history=chat_history,
                )
                if choices and choices.choices:
                    self.ui_queue.put({"type": "choices", "choices": choices.choices})
            except Exception as e:
                self.logger.error(
                    f"Error generating action choices: {e}", exc_info=True
                )

        # ===== NOW add narrative to chat history (all phases complete) =====
        session_in_thread.add_message("assistant", narrative.response)

        # We must reload the session metadata because tools like RequestSetupConfirmation
        # updated the DB directly, but our 'game_session' object here is stale.
        if thread_db_manager.sessions:
            latest_session_state = thread_db_manager.sessions.get_by_id(game_session.id)
            if latest_session_state:
                game_session.setup_phase_data = latest_session_state.setup_phase_data
                game_session.game_mode = latest_session_state.game_mode
                # Note: game_time usually updates via tools too, so good to refresh
                game_session.game_time = latest_session_state.game_time

        # Now save the history (without overwriting the flags we just refreshed)
        self.orchestrator._update_game_in_thread(
            game_session, thread_db_manager, session_in_thread
        )

    def _summarize_previous_scene(self, game_session, db, current_round):
        """
        Gathers turns from the previous scene and condenses them into a summary.
        """
        try:
            # 1. Find start of current scene (last time a summary was made)
            last_scenes = db.turn_metadata.get_recent_scenes(game_session.id, limit=1)
            # start_turn = 0
            if last_scenes:
                # This is approximate; ideally we store 'end_turn_id' in the scene table
                # For MVP, we assume scene boundary is implied.
                pass

            # 2. Get Turn Metadata since then
            # We need a way to query turns *since* the last summary.
            # This requires the scene_history table to track 'end_turn_id'.
            # Let's assume we fetch the last 20 turns and rely on the LLM to figure it out?
            # Better: Fetch all turns, but that's expensive.
            # Optimization: Just summarize the *chat history* currently in the context window
            # before we clear it for the new scene.

            history_text = "\n".join(
                [
                    f"{m.role}: {m.content}"
                    for m in Session.from_json(game_session.session_data).get_history()[
                        -20:
                    ]
                ]
            )

            prompt = SCENE_SUMMARIZATION_TEMPLATE.format(history=history_text)

            response_obj = self.llm_connector.get_structured_response(
                prompt, [], SceneSummary
            )
            summary = response_obj.summary_text
            self.logger.info(f"Scene summarization triggered. Summary: {summary}")

        except Exception as e:
            self.logger.error(f"Scene summarization failed: {e}")

    # NOTE: The _execute_world_tick method has been removed. Its functionality is being
    # replaced by a just-in-time simulation service triggered by the ContextBuilder.
