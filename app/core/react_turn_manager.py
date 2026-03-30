import json
import logging
import threading
from typing import Dict, Type
from pydantic import BaseModel
from app.context.context_builder import ContextBuilder
from app.context.memory_retriever import MemoryRetriever
from app.context.state_context import StateContextBuilder
from app.core.simulation_service import SimulationService
from app.models.game_session import GameSession
from app.models.message import Message
from app.models.session import Session
from app.setup.setup_manifest import SetupManifest
from app.tools.executor import ToolExecutor
from app.tools.schemas import Adjust, Set, Mark, Roll, Move, Note, ContextRetrieve, NpcSpawn, LocationCreate, StateQuery
from app.llm.schemas import TurnSuggestions, TurnMetadata

logger = logging.getLogger(__name__)

MAX_HISTORY_MESSAGES = 50
MAX_REACT_LOOPS = 15


class ReActTurnManager:
    """
    Executes a game turn using an Iterative ReAct (Reason + Act) Loop.
    Lifecycle-aware: attaches turn_id to all UI events.
    Integration: Loads SystemManifest for Context and Tools.
    """

    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.logger = orchestrator.logger
        self.llm_connector = orchestrator.llm_connector
        self.tool_registry = orchestrator.tool_registry
        self.vector_store = orchestrator.vector_store
        self.ui_queue = orchestrator.ui_queue
        self.tool_map: Dict[str, Type[BaseModel]] = {
            t.model_fields["name"].default: t
            for t in self.tool_registry.get_all_tool_types()
        }

    def execute_turn(self, game_session: GameSession, thread_db_manager, turn_id: str):
        if self.orchestrator.stop_event.is_set():
            return
        # --- 1. LOAD MANIFEST ---
        # Fetch the active system manifest for this session
        manifest_mgr = SetupManifest(thread_db_manager)
        setup_data = manifest_mgr.get_manifest(game_session.id)
        # Determine Manifest ID
        manifest_id = setup_data.get("manifest_id")
        manifest = None
        if manifest_id:
            manifest = thread_db_manager.manifests.get_by_id(manifest_id)
        # If manifest is not loaded/valid, show error to the user
        if not manifest:
            error_msg = (
                "⚠️ Game system not configured. "
                "Please select a game system in the Session Setup before playing."
            )
            self.ui_queue.put({
                "type": "error",
                "message": error_msg,
                "turn_id": turn_id,
            })
            return
        # --- 2. SETUP SERVICES ---
        state_builder = StateContextBuilder(
            self.tool_registry, thread_db_manager, self.logger
        )
        mem_retriever = MemoryRetriever(
            thread_db_manager, self.vector_store, self.logger
        )
        sim_service = SimulationService(self.llm_connector, self.logger)
        # Pass Manifest to Context Builder
        context_builder = ContextBuilder(
            thread_db_manager,
            self.vector_store,
            state_builder,
            mem_retriever,
            sim_service,
            logger=self.logger,
            manifest=manifest,
        )
        executor = ToolExecutor(
            self.tool_registry,
            thread_db_manager,
            self.vector_store,
            self.ui_queue,
            self.logger,
        )
        # --- 3. CONTEXT BUILDING ---
        session_in_thread = Session.from_json(game_session.session_data)
        session_in_thread.id = game_session.id
        static_instruction = context_builder.build_static_system_instruction(
            game_session
        )
        chat_history = context_builder.get_truncated_history(
            session_in_thread, MAX_HISTORY_MESSAGES
        )
        working_history = list(chat_history)
        working_history = self._prepend_rolling_summary(game_session, working_history)
        
        mems = mem_retriever.get_relevant(
            session_in_thread,
            recent_messages=working_history,
        )

        dynamic_context = context_builder.build_dynamic_context(
            game_session, chat_history, rag_memories=mems
        )
        turn_system_prompt = f"{static_instruction}\n\n{dynamic_context}"
        
        if mems:
            # Emit UI event for debug visibility
            rag_text_for_ui = mem_retriever.format_for_prompt(mems)

            # Append the rag context as a tool return message
            tool_return_message = Message(
                role="tool",
                name="rag_context",
                content=rag_text_for_ui,
                turn_id=turn_id,
            )
            working_history.append(tool_return_message)
            
            # Flatten memory IDs for the UI queue
            flat_mem_ids = [m.id for cat_mems in mems.values() for m in cat_mems]

            self.ui_queue.put(
                {
                    "type": "rag_context",
                    "text": rag_text_for_ui,
                    "memory_ids": flat_mem_ids,
                    "turn_id": turn_id,
                }
            )
        # --- 4. TOOL INJECTION ---
        active_tool_names = [
            Roll.model_fields["name"].default,

            Adjust.model_fields["name"].default,
            Set.model_fields["name"].default,
            Mark.model_fields["name"].default,

            Move.model_fields["name"].default,

            Note.model_fields["name"].default,
            ContextRetrieve.model_fields["name"].default,
            StateQuery.model_fields["name"].default,

            NpcSpawn.model_fields["name"].default,
            LocationCreate.model_fields["name"].default,
        ]
        llm_tools = self.tool_registry.get_llm_tool_schemas(active_tool_names)
        # Inject Dice Rules into Roll Tool
        if manifest:
            for tool in llm_tools:
                if tool["function"]["name"] == "roll":
                    eng = manifest.engine
                    desc = (
                        f"Roll dice. SYSTEM: Dice='{eng.dice}'. "
                        f"Mechanic='{eng.mechanic}'. "
                        f"Crit='{eng.crit}'."
                    )
                    tool["function"]["description"] = desc

        # Appends the list of available tools to the working history
        tools_defs = "Autonomously use the following tools to perform actions, retrieve information, create, or modify game elements, etc.\n\n```available_tools\n"
        for tool in llm_tools:
            name = tool["function"]["name"]
            desc = tool["function"]["description"].strip()
            # Clean up docstring formatting
            desc = " ".join(desc.split())
            tools_defs += f"- **{name}**: {desc}\n"
        tools_defs += "\n```"

        tool_message = Message(
            role="tool",
            name="available_tools",
            content=tools_defs,
            turn_id=turn_id,
        )
        working_history.append(tool_message)
        
        # --- 5. ACTION LOOP ---
        loop_count = 0
        narrative_text = ""
        while loop_count < MAX_REACT_LOOPS:
            if self.orchestrator.stop_event.is_set():
                self.ui_queue.put(
                    {"type": "error", "message": "Stopped by user.", "turn_id": turn_id}
                )
                return
            loop_count += 1
            try:
                response = self.llm_connector.chat_with_tools(
                    system_prompt=turn_system_prompt,
                    chat_history=working_history,
                    tools=llm_tools,
                )
            except Exception as e:
                if self.orchestrator.stop_event.is_set():
                    return
                raise e
                
            assistant_msg = Message(
                role="assistant",
                content=response.content,
                thought=response.thought,
                thought_signature=response.thought_signature,
                tool_calls=response.tool_calls,
            )
            working_history.append(assistant_msg)
            
            if response.content and not response.tool_calls:
                self.ui_queue.put(
                    {
                        "type": "message_bubble",
                        "role": "assistant",
                        "content": response.content,
                        "turn_id": turn_id,
                    }
                )
                narrative_text = response.content
                break

            if response.tool_calls:
                self.logger.info(
                    f"ReAct Loop {loop_count}: Model called {len(response.tool_calls)} tools."
                )
                if response.thought:
                    self.ui_queue.put(
                        {
                            "type": "thought_bubble",
                            "content": response.thought,
                            "turn_id": turn_id,
                        }
                    )
                if response.content:
                    self.ui_queue.put(
                        {
                            "type": "thought_bubble",
                            "content": response.content,
                            "turn_id": turn_id,
                        }
                    )
                for call_data in response.tool_calls:
                    if self.orchestrator.stop_event.is_set():
                        return

                    call_id = call_data.get("id", "call_default")
                    name = call_data["name"]
                    args = call_data["arguments"]
                    if name in self.tool_map:
                        try:
                            pydantic_model = self.tool_map[name](**args)
                            extra_ctx = {
                                "simulation_service": sim_service,
                                "manifest": manifest,  # PASS MANIFEST TO TOOLS
                            }
                            result, _ = executor.execute(
                                [pydantic_model],
                                game_session,
                                setup_data,  # Pass setup data as manifest dict fallback
                                tool_budget=1,
                                current_game_time=game_session.game_time,
                                extra_context=extra_ctx,
                                turn_id=turn_id,
                            )
                            res_data = (
                                result[0]["result"]
                                if result
                                else {"error": "No result returned"}
                            )
                            tool_msg = Message(
                                role="tool",
                                tool_call_id=call_id,
                                name=name,
                                content=json.dumps(res_data, indent=2),
                            )
                            working_history.append(tool_msg)
                        except Exception as e:
                            error_msg = Message(
                                role="tool",
                                tool_call_id=call_id,
                                name=name,
                                content=json.dumps({"error": str(e)}, indent=2),
                            )
                            working_history.append(error_msg)
                            self.ui_queue.put(
                                {
                                    "type": "tool_result",
                                    "result": str(e),
                                    "is_error": True,
                                    "turn_id": turn_id,
                                }
                            )
                    else:
                        error_msg = Message(
                            role="tool",
                            tool_call_id=call_id,
                            name=name,
                            content=json.dumps({"error": f"Tool '{name}' not found."}, indent=2),
                        )
                        working_history.append(error_msg)
                continue

        # --- 5B. LOOP EXHAUSTION GUARD ---
        if not narrative_text:
            self.logger.warning(
                f"ReAct loop exhausted without narrative. Forcing narrative generation. Turn ID: {turn_id}"
            )
            # Make one final streaming response call to force a text response
            try:
                fallback_response = self.llm_connector.stream_response(
                    system_prompt=turn_system_prompt,
                    chat_history=working_history,
                )
                narrative_text = "".join(fallback_response)
                if narrative_text:
                    self.ui_queue.put(
                        {
                            "type": "message_bubble",
                            "role": "assistant",
                            "content": narrative_text,
                            "turn_id": turn_id,
                        }
                    )
            except Exception as fallback_e:
                self.logger.error(f"Fallback narrative generation failed: {fallback_e}")
                
        # --- 6. TIER 1: SYNCHRONOUS SUGGESTIONS ---
        if self.orchestrator.stop_event.is_set() or not narrative_text:
            return
            
        choices = []
        try:
            # Prepare minimal history for suggestions
            final_history = list(working_history)
            if not any(m.content == narrative_text for m in final_history if m.role == "assistant"):
                 final_history.append(Message(role="assistant", content=narrative_text))

            final_history.append(
                Message(
                    role="user",
                    content="Write 3-5 action options the Player could take next, in first person, in the format: \"I do X\", \"I go to Y\", etc. Return strictly as JSON.",
                )
            )
            
            # Fast, small schema call
            suggestions_out = self.llm_connector.get_structured_response(
                system_prompt=turn_system_prompt,
                chat_history=final_history,
                output_schema=TurnSuggestions,
                temperature=0.7,
            )
            choices = list(suggestions_out.choices or [])
            
        except Exception as e:
            self.logger.warning(f"Turn suggestions generation failed: {e}")
        
        # --- 7. PERSISTENCE (NARRATIVE) ---
        if narrative_text.strip():
            session_in_thread.add_message("assistant", narrative_text)
            
        self.orchestrator._update_game_in_thread(
            game_session, thread_db_manager, session_in_thread
        )

        if choices:
            self.ui_queue.put(
                {
                    "type": "choices",
                    "choices": choices,
                    "turn_id": turn_id,
                }
            )

        # --- 8. TIER 2: BACKGROUND CHRONICLER ---
        # Spawn thread for summary, tags, and importance
        chronicler_thread = threading.Thread(
            target=self._run_chronicler_task,
            args=(
                game_session.id,
                working_history,
                narrative_text,
                turn_id,
                turn_system_prompt
            ),
            daemon=True,
            name=f"Chronicler-{game_session.id}-{turn_id}"
        )
        chronicler_thread.start()

    def _run_chronicler_task(
        self,
        session_id: int,
        working_history: list[Message],
        narrative_text: str,
        turn_id: str,
        turn_system_prompt: str
    ):
        """
        Background task to generate turn summary, tags, and importance.
        Uses its own DB connection for thread safety.
        """
        self.logger.debug(f"Starting background chronicler for session {session_id}")
        
        try:
            # Prepare metadata context
            final_history = list(working_history)
            if not any(m.content == narrative_text for m in final_history if m.role == "assistant"):
                 final_history.append(Message(role="assistant", content=narrative_text))

            final_history.append(
                Message(
                    role="user",
                    content=(
                        "Summarize this scene, generate tags that describe the scene, and provide an importance rating.\n"
                        "1. Provide a concise 1-3 sentence summary.\n"
                        "2. Provide snake_case tags.\n"
                        "3. Rate importance 1-5.\n"
                        "Return strictly as JSON."
                    ),
                )
            )

            metadata_out = self.llm_connector.get_structured_response(
                system_prompt=turn_system_prompt,
                chat_history=final_history,
                output_schema=TurnMetadata,
                temperature=0.5,
            )

            # Persist with new DB connection
            from app.database.db_manager import DBManager
            from app.core.metadata.turn_metadata_service import TurnMetadataService
            with DBManager(self.orchestrator.db_path) as db:
                turnmeta = TurnMetadataService(db, self.vector_store)
                
                # Fetch rolling history to get round number
                game_session = db.sessions.get_by_id(session_id)
                full_session = Session.from_json(game_session.session_data)
                
                turnmeta.persist(
                    session_id=session_id,
                    prompt_id=game_session.prompt_id,
                    round_number=len(full_session.get_history()) // 2,
                    summary=(metadata_out.summary or "").strip(),
                    tags=[t.strip() for t in metadata_out.tags if isinstance(t, str) and t.strip()],
                    importance=int(metadata_out.importance or 3),
                )
            
            self.logger.info(f"Background chronicler complete for session {session_id}")
                
        except Exception as e:
            self.logger.error(f"Background chronicler failed: {e}", exc_info=True)

    def _prepend_rolling_summary(
        self, game_session: GameSession, history: list[Message]
    ) -> list[Message]:
        """
        Option 2: inject summary as a single first message, choosing role to avoid
        same-role adjacency with the first real message.
        """
        summary = (game_session.memory or "").strip()
        if not summary:
            return history
        # Determine first real role
        first_real_role = history[0].role if history else "user"
        # Choose opposite role to preserve alternation (user-user / assistant-assistant avoidance)
        prefix_role = "assistant" if first_real_role == "user" else "user"
        prefix = Message(
            role=prefix_role,
            content=f"# STORY SO FAR\n{summary}",
        )
        return [prefix] + history


