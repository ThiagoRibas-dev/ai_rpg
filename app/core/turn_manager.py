# File: app/core/turn_manager.py


# Import from new locations
from app.context.context_builder import ContextBuilder
from app.context.memory_retriever import MemoryRetriever
from app.context.state_context import StateContextBuilder
from app.context.world_info_service import WorldInfoService
from app.llm.auditor_service import AuditorService
from app.llm.choices_service import ChoicesService
from app.llm.narrator_service import NarratorService
from app.llm.planner_service import PlannerService
from app.prompts.templates import (
    CHOICE_GENERATION_TEMPLATE,
    NARRATIVE_TEMPLATE,
    PLAN_TEMPLATE,
    SETUP_PLAN_TEMPLATE,
    SETUP_RESPONSE_TEMPLATE,
)
from app.prompts.builder import build_lean_schema_reference
from app.memory.memory_intents_service import MemoryIntentsService
from app.core.metadata.turn_metadata_service import TurnMetadataService
from app.tools.executor import ToolExecutor
from app.database.db_manager import DBManager
from app.models.game_session import GameSession
from app.models.session import Session
from app.tools.schemas import EndSetupAndStartGameplay, Patch, SchemaDefineProperty, StateApplyPatch, SchemaQuery, Deliberate
from app.setup.setup_manifest import SetupManifest

MAX_HISTORY_MESSAGES = 20
TOOL_BUDGET = 10

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
        state_builder = StateContextBuilder(self.tool_registry, thread_db_manager, self.logger)
        mem_retriever = MemoryRetriever(thread_db_manager, self.vector_store, self.logger)
        turnmeta = TurnMetadataService(thread_db_manager, self.vector_store)
        world_info = WorldInfoService(thread_db_manager, self.vector_store, self.logger)
        context_builder = ContextBuilder(
            thread_db_manager, self.vector_store, state_builder, mem_retriever, turnmeta, world_info, self.logger
        )
        executor = ToolExecutor(
            self.tool_registry, thread_db_manager, self.vector_store, ui_queue=self.ui_queue, logger=self.logger
        )
        auditor = AuditorService(
            self.llm_connector, self.tool_registry, thread_db_manager, self.vector_store, self.logger
        )
        mem_intents = MemoryIntentsService(
            self.tool_registry, thread_db_manager, self.vector_store, self.logger
        )

        # Determine game mode and available tools
        current_game_mode = game_session.game_mode
        if current_game_mode == "SETUP":
            setup_tool_names = [
                SchemaDefineProperty.model_fields["name"].default, 
                Deliberate.model_fields["name"].default, 
                SchemaQuery.model_fields["name"].default, 
                EndSetupAndStartGameplay.model_fields["name"].default
            ]
            available_tool_models = self.tool_registry.get_tool_models(setup_tool_names)
            available_tool_schemas_json = [s for s in self.tool_registry.get_all_schemas() if s["name"] in setup_tool_names]
        else:  # GAMEPLAY mode
            available_tool_models = self.tool_registry.get_all_tool_types()
            available_tool_schemas_json = self.tool_registry.get_all_schemas()

        # ===== BUILD STATIC SYSTEM INSTRUCTION =====
        manifest_mgr = SetupManifest(thread_db_manager)
        manifest = manifest_mgr.get_manifest(game_session.id)
        schema_ref = build_lean_schema_reference(manifest)
        static_instruction = context_builder.build_static_system_instruction(
            game_session, available_tool_schemas_json, schema_ref
        )

        # ===== BUILD CHAT HISTORY (ONCE, before all phases) =====
        chat_history = context_builder.get_truncated_history(session_in_thread, MAX_HISTORY_MESSAGES)
        
        # ===== BUILD DYNAMIC CONTEXT =====
        dynamic_context = context_builder.build_dynamic_context(game_session, chat_history)

        # ===== STEP 1: PLAN =====
        phase_template = SETUP_PLAN_TEMPLATE if current_game_mode == "SETUP" else PLAN_TEMPLATE.format(tool_budget=TOOL_BUDGET)
        plan = self.planner.plan(
            system_instruction=static_instruction, phase_template=phase_template, dynamic_context=dynamic_context, chat_history=chat_history, available_tool_models=available_tool_models
        )
        if not plan:
            self.logger.error("LLM returned no structured response for TurnPlan.")
            self.ui_queue.put({"type": "error", "message": "AI failed to generate a valid plan."})
            return
        
        plan_steps_text = "\n - ".join(plan.plan_steps)
        plan_summary = f"""{plan.player_input_analysis}\n\n{plan_steps_text}\n\n{plan.narrative_plan}"""

        self.ui_queue.put({"type": "thought_bubble", "content": plan_summary})

        # ===== STEP 2: EXECUTE TOOLS =====
        tool_results, memory_tool_used = executor.execute(
            plan.tool_calls, game_session, TOOL_BUDGET, current_game_time=getattr(game_session, "game_time", None)
        )
        if memory_tool_used and hasattr(self.orchestrator.view, "memory_inspector"):
            self.ui_queue.put({"type": "refresh_memory_inspector"})

        for result in tool_results:
            if result.get("tool_name") == EndSetupAndStartGameplay.model_fields["name"].default and result.get("result", {}).get("setup_complete"):
                game_session.game_mode = "GAMEPLAY"
                self.ui_queue.put({"type": "update_game_mode", "new_mode": "GAMEPLAY"})
                self.ui_queue.put({"type": "message_bubble", "role": "system", "content": "✅ Session Zero complete! Game starting..."})
                self.orchestrator._update_game_in_thread(game_session, thread_db_manager, session_in_thread)

        # ===== STEP 2.5: AUDIT (only in GAMEPLAY mode) =====
        if current_game_mode == "GAMEPLAY":
            audit_history = context_builder.get_truncated_history(session_in_thread, MAX_HISTORY_MESSAGES)
            audit = auditor.audit(audit_history, tool_results)
            if audit and not audit.ok:
                auditor.apply_remediations(audit, game_session)

        # ===== STEP 3: NARRATIVE/RESPONSE =====
        dynamic_context = context_builder.build_dynamic_context(game_session, chat_history)
        phase_template = SETUP_RESPONSE_TEMPLATE if current_game_mode == "SETUP" else NARRATIVE_TEMPLATE
        narrative = self.narrator.write_step(
            system_instruction=static_instruction, phase_template=phase_template, dynamic_context=dynamic_context, plan_thought=plan_summary, tool_results=str(tool_results), chat_history=chat_history
        )
        if not narrative:
            self.logger.error("LLM returned no structured response for NarrativeStep.")
            self.ui_queue.put({"type": "error", "message": "AI failed to generate a valid narrative."})
            return
        self.ui_queue.put({"type": "message_bubble", "role": "assistant", "content": narrative.response})

        # ===== STEP 3.5: Turn metadata =====
        if current_game_mode == "GAMEPLAY" and game_session.id:
            round_number = len(session_in_thread.get_history()) // 2 + 1
            turnmeta.persist(
                session_id=game_session.id, prompt_id=game_session.prompt_id, round_number=round_number, summary=narrative.turn_summary, tags=narrative.turn_tags, importance=narrative.turn_importance
            )

        # ===== STEP 4: Apply patches and memory intents =====
        if narrative.proposed_patches:
            for patch in narrative.proposed_patches:
                try:
                    patch_call = StateApplyPatch(entity_type=patch.entity_type, key=patch.key, patch=[Patch(**op.model_dump()) for op in patch.ops])
                    result = self.tool_registry.execute(patch_call, context={"session_id": game_session.id, "db_manager": thread_db_manager})
                    if self.orchestrator.tool_event_callback:
                        self.ui_queue.put({"type": "tool_event", "message": f"{StateApplyPatch.model_fields['name'].default} ✓ → {result}"})
                except Exception as e:
                    self.logger.error(f"Patch error: {e}")
        mem_intents.apply(narrative.memory_intents, session_in_thread, tool_event_callback=self.orchestrator.tool_event_callback)
        
        # ===== STEP 5: Action choices =====
        if current_game_mode == "GAMEPLAY":
            try:
                choices = self.choices.generate(
                    system_instruction=static_instruction, phase_template=CHOICE_GENERATION_TEMPLATE, narrative_text=narrative.response, chat_history=chat_history
                )
                if choices and choices.choices:
                    self.ui_queue.put({"type": "choices", "choices": choices.choices})
            except Exception as e:
                self.logger.error(f"Error generating action choices: {e}", exc_info=True)

        # ===== NOW add narrative to chat history (all phases complete) =====
        session_in_thread.add_message("assistant", narrative.response)
        
        # Persist final session state
        self.orchestrator._update_game_in_thread(game_session, thread_db_manager, session_in_thread)
