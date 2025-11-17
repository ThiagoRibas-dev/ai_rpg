import logging
import random  # Import the random module for probability checks
from app.context.context_builder import ContextBuilder
from app.context.memory_retriever import MemoryRetriever
from app.context.state_context import StateContextBuilder
from app.core.metadata.turn_metadata_service import TurnMetadataService
from app.models.npc_profile import NpcProfile
from app.database.db_manager import DBManager
from app.llm.llm_connector import LLMConnector
from app.llm.auditor_service import AuditorService
from app.llm.choices_service import ChoicesService
from app.llm.narrator_service import NarratorService
from app.llm.planner_service import PlannerService
from app.llm.schemas import WorldTickOutcome
from app.memory.memory_intents_service import MemoryIntentsService
from app.models.game_session import GameSession
from app.models.session import Session
from app.prompts.builder import build_lean_schema_reference
from app.prompts.templates import (
    GAMEPLAY_PLAN_TEMPLATE,
    SETUP_PLAN_TEMPLATE,
    CHOICE_GENERATION_TEMPLATE,
    NARRATIVE_TEMPLATE,
    SETUP_RESPONSE_TEMPLATE,
    TOOL_SELECTION_PER_STEP_TEMPLATE,
    WORLD_TICK_SIMULATION_TEMPLATE,
)
from app.setup.setup_manifest import SetupManifest
from app.tools.executor import ToolExecutor
# Import the handler directly to apply patches without a full tool execution loop
from app.tools.builtin.state_apply_patch import handler as apply_patch_handler
from app.tools.schemas import (
    Deliberate,
    EndSetupAndStartGameplay,
    Patch,
    SchemaUpsertAttribute,
    StateApplyPatch,
    SchemaQuery,
)

MAX_HISTORY_MESSAGES = 50
TOOL_BUDGET = 10

logger = logging.getLogger(__name__)


class WorldTickService:
    """Encapsulates the LLM call for simulating NPC actions."""
    def __init__(self, llm: LLMConnector, logger: logging.Logger):
        self.llm = llm
        self.logger = logger

    def simulate_npc_action(
        self, npc_name: str, profile: NpcProfile, duration_desc: str
    ) -> WorldTickOutcome | None:
        """Calls the LLM to get a simulated outcome for an NPC's directive."""
        try:
            prompt = WORLD_TICK_SIMULATION_TEMPLATE.format(
                npc_name=npc_name,
                personality=", ".join(profile.personality_traits),
                motivations=", ".join(profile.motivations),
                duration_desc=duration_desc,
                directive=profile.directive,
            )
            
            # We use a system prompt here as there is no conversational history.
            outcome = self.llm.get_structured_response(
                system_prompt=prompt,
                chat_history=[],
                output_schema=WorldTickOutcome,
            )
            return outcome # Mypy will infer this as WorldTickOutcome due to output_schema
        except Exception as e:
            self.logger.error(
                f"World Tick LLM simulation failed for NPC {npc_name}: {e}",
                exc_info=True,
            )
            return None


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
        turnmeta = TurnMetadataService(thread_db_manager, self.vector_store)
        context_builder = ContextBuilder(
            thread_db_manager,
            self.vector_store,
            state_builder,
            mem_retriever,
            turnmeta,
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
        mem_intents = MemoryIntentsService(
            self.tool_registry, thread_db_manager, self.vector_store, self.logger
        )

        # Determine game mode and available tools
        current_game_mode = game_session.game_mode
        if current_game_mode == "SETUP":
            setup_tool_names = [
                SchemaUpsertAttribute.model_fields["name"].default,
                Deliberate.model_fields["name"].default,
                SchemaQuery.model_fields["name"].default,
                EndSetupAndStartGameplay.model_fields["name"].default,
            ]
        else:  # GAMEPLAY mode
            setup_tool_names = self.tool_registry.get_all_tool_names()  # Use all tools

        # ===== BUILD STATIC SYSTEM INSTRUCTION =====
        manifest_mgr: SetupManifest = SetupManifest(thread_db_manager)
        manifest = manifest_mgr.get_manifest(game_session.id)
        schema_ref = build_lean_schema_reference(manifest)
        # Tool schemas are no longer passed into the static instruction
        static_instruction = context_builder.build_static_system_instruction(
            game_session, schema_ref
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
        self.ui_queue.put(
            {"type": "planning_started", "content": "Planning..."}
        )

        # Phase 1: Create Plan (Analysis + Strategy)
        if current_game_mode == "SETUP":
            plan_template = SETUP_PLAN_TEMPLATE
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
            self.logger.debug(f"Starting iterative tool selection for {len(plan_steps)} steps.")
            for i, step in enumerate(plan_steps):
                self.logger.debug(f"  -> Selecting tool for step {i+1}: '{step}'")
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
                    self.logger.debug(f"  <- Selected {len(step_tool_calls)} tool(s) for step {i+1}.")
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
        if memory_tool_used and hasattr(self.orchestrator.view, "memory_inspector"):
            # Special hook for time.advance to trigger world ticks
            for result in tool_results:
                if result.get("name") == "time.advance" and result.get("result"):
                    self._execute_world_tick(game_session, thread_db_manager, result["result"])

            self.ui_queue.put({"type": "refresh_memory_inspector"})

        for result in tool_results:
            if result.get("name") == EndSetupAndStartGameplay.model_fields[
                "name"
            ].default and result.get("result", {}).get("setup_complete"):
                game_session.game_mode = "GAMEPLAY"
                self.ui_queue.put({"type": "update_game_mode", "new_mode": "GAMEPLAY"})
                self.ui_queue.put(
                    {
                        "type": "message_bubble",
                        "role": "system",
                        "content": "✅… Session Zero complete! Game starting...",
                    }
                )
                self.orchestrator._update_game_in_thread(
                    game_session, thread_db_manager, session_in_thread
                )
                return self.execute_turn(game_session, thread_db_manager)
        
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
        narrative = self.narrator.write_step(
            system_instruction=static_instruction,
            phase_template=phase_template,
            dynamic_context=dynamic_context,
            plan_thought=plan_summary,
            tool_results=str(tool_results),
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

        # ===== STEP 4: Apply patches and memory intents =====
        if narrative.proposed_patches:
            for patch in narrative.proposed_patches:
                try:
                    patch_call = StateApplyPatch(
                        entity_type=patch.entity_type,
                        key=patch.key,
                        patch=[Patch(**op.model_dump()) for op in patch.ops],
                    )
                    result = self.tool_registry.execute(
                        patch_call,
                        context={
                            "session_id": game_session.id,
                            "db_manager": thread_db_manager,
                        },
                    )
                    if self.orchestrator.tool_event_callback:
                        self.ui_queue.put(
                            {
                                "type": "tool_event",
                                "message": f"{StateApplyPatch.model_fields['name'].default} ✔️ {result}",
                            }
                        )
                except Exception as e:
                    self.logger.error(f"Patch error: {e}", exc_info=True)
        mem_intents.apply(
            narrative.memory_intents,
            session_in_thread,
            tool_event_callback=self.orchestrator.tool_event_callback,
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

        # Persist final session state
        self.orchestrator._update_game_in_thread(
            game_session, thread_db_manager, session_in_thread
        )

    def _execute_world_tick(self, game_session: GameSession, db: DBManager, time_advance_result: dict):
        """
        Simulates off-screen NPC actions during a time skip.
        This is a non-LLM, logic-based process to create emergent story events.
        """
        TICK_EVENT_PROBABILITY_PER_DAY = 0.15 # 15% chance of a noteworthy event per NPC per day.

        duration_hours = time_advance_result.get("duration_hours", 0)
        if duration_hours < 1:
            return # Don't run simulation for short time skips

        logger.info(f"Executing world tick for a duration of {duration_hours} hours...")
        
        # Instantiate the service for LLM calls
        tick_service = WorldTickService(self.llm_connector, self.logger)

        # Get all NPC profiles
        if db.game_state is None:
            self.logger.error("DBManager.game_state is None, cannot execute world tick.")
            return
        all_profiles_data = db.game_state.get_all_entities_by_type(game_session.id, "npc_profile")
        days_passed = max(1, duration_hours // 24)

        for npc_key, profile_data in all_profiles_data.items():
            profile = NpcProfile(**profile_data)
            # Only process NPCs that have an active directive.
            if not profile.directive or profile.directive == "idle":
                continue

            # Roll the dice for each day that passed to see if a noteworthy event occurs.
            for _ in range(days_passed):
                if random.random() < TICK_EVENT_PROBABILITY_PER_DAY:
                    self.logger.info(f"World tick event triggered for NPC: {npc_key}")
                    
                    char_data = db.game_state.get_entity(game_session.id, "character", npc_key)
                    npc_name = char_data.get("name", npc_key)
                    
                    # Call the LLM to determine the outcome
                    outcome = tick_service.simulate_npc_action(
                        npc_name=npc_name,
                        profile=profile,
                        duration_desc=time_advance_result.get("description", "some time")
                    )

                    if not outcome:
                        continue # LLM call failed, move to next NPC

                    # 1. Apply any state changes proposed by the LLM
                    if outcome.proposed_patches:
                        for patch_intent in outcome.proposed_patches:
                            try:
                                patch_ops_dicts = [op.model_dump() for op in patch_intent.ops]
                                apply_patch_handler(
                                    entity_type=patch_intent.entity_type,
                                    key=patch_intent.key,
                                    patch=patch_ops_dicts,
                                    session_id=game_session.id,
                                    db_manager=db
                                )
                                self.logger.info(f"Applied world tick patch for {patch_intent.key}: {patch_ops_dicts}")
                            except Exception as e:
                                self.logger.error(f"Failed to apply world tick patch: {e}", exc_info=True)

                    # 2. Conditionally create a memory if the event was significant
                    if outcome.is_significant:
                        if db.memories is None:
                            self.logger.error("DBManager.memories is None, cannot create memory.")
                            continue
                        db.memories.create(
                            session_id=game_session.id,
                            kind="episodic",
                            content=outcome.outcome_summary,
                            priority=2, # A bit higher than mundane ticks
                            tags=["world_tick", "emergent_event", npc_key],
                            fictional_time=time_advance_result.get("new_time")
                        )
                        self.logger.info(f"Created significant memory for {npc_key}: {outcome.outcome_summary}")
                    
                    # Only process one event per NPC per time skip to keep it clean.
                    break 

        logger.info(f"World tick complete. Processed {len(all_profiles_data)} NPCs.")
