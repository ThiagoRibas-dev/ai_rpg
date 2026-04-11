import json
import logging
import os
import threading
from typing import Any

from pydantic import BaseModel

from app.context.context_builder import ContextBuilder
from app.context.memory_retriever import MemoryRetriever
from app.context.state_context import StateContextBuilder
from app.core.metadata.turn_metadata_service import TurnMetadataService
from app.core.simulation_service import SimulationService
from app.database.db_manager import DBManager
from app.llm.schemas import TurnMetadata, TurnSuggestions
from app.models.game_session import GameSession
from app.models.message import Message
from app.models.session import Session
from app.models.vocabulary import MessageRole, UIEventType
from app.setup.setup_manifest import SetupManifest
from app.tools.executor import ToolExecutor
from app.tools.schemas import Adjust, ContextRetrieve, LocationCreate, Mark, Move, Note, NpcSpawn, Roll, Set, StateQuery

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
        self.tool_map: dict[str, type[BaseModel]] = {
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
            system_error = (
                "⚠️ Game system not configured. "
                "Please select a game system in the Session Setup before playing."
            )
            self.logger.error(system_error)
            self.ui_queue.put({
                "type": UIEventType.ERROR,
                "message": system_error,
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
        sim_service = SimulationService(
            self.llm_connector, self.logger, stop_event=self.orchestrator.stop_event
        )
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

        dynamic_context = context_builder.build_dynamic_context(
            game_session, chat_history
        )
        turn_system_prompt = f"{static_instruction}\n\n{dynamic_context}"

        mems = mem_retriever.get_relevant(
            session_in_thread,
            recent_messages=working_history,
        )

        # Staged synthetic tool messages — collected here, injected after a synthetic
        # assistant message so the history is OpenAI-standard compliant.
        synthetic_tool_messages: dict[str, Message] = {}

        if mems:
            # Emit UI event for debug visibility
            rag_text_for_ui = mem_retriever.format_for_prompt(mems)

            # Stage the rag context as a synthetic tool return message
            if rag_text_for_ui:
                synthetic_tool_messages["passive_rag_context"] = Message(
                    role=MessageRole.TOOL,
                    tool_call_id="passive_rag_context",
                    name="passive_rag_context",
                    content=rag_text_for_ui,
                    turn_id=turn_id,
                )

            # Flatten memory IDs for the UI queue
            flat_mem_ids = [m.id for cat_mems in mems.values() for m in cat_mems]

            self.ui_queue.put(
                {
                    "type": UIEventType.RAG_CONTEXT,
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
                        f"{tool['function']['description']}\n"
                        f"SYSTEM: Dice='{eng.dice}'. "
                        f"Mechanic='{eng.mechanic}'. "
                        f"Crit='{eng.crit}'.\n"
                        "You must use this tool any time a dice roll is involved. Never 'simulate' a roll."
                    )
                    tool["function"]["description"] = desc

        # Appends the list of available tools to the working history
        tools_defs = "I have access to the following tools to retrieve or confirm information, roll dice, create or modify Game State, etc.\n\n```available_tools\n"
        for tool in llm_tools:
            name = tool["function"]["name"]
            desc = tool["function"]["description"].strip()
            # Clean up docstring formatting
            desc = " ".join(desc.split())
            tools_defs += f"- **{name}**: {desc}\n"
        tools_defs += "\n```\n\nI will use the dice tool to make decisions, create entropy, simulate outcomes, etc.\n\nI will also proactively decide which tools/functions to use and when.\n"

        # Stage the tool definitions as a synthetic tool return message
        if tools_defs:
            synthetic_tool_messages["available_tools"] = Message(
                role=MessageRole.TOOL,
                tool_call_id="tools_defs",
                name="available_tools",
                content=tools_defs,
                turn_id=turn_id,
            )

        # Inject synthetic tool context (RAG, tool definitions, etc.)
        working_history_request = self._get_request_history_with_synthetic_tools(
            working_history, synthetic_tool_messages, turn_id
        )


        # --- 5. ACTION LOOP ---
        loop_count = 0
        narrative_text = ""
        while loop_count < MAX_REACT_LOOPS:
            if self.orchestrator.stop_event.is_set():
                self.ui_queue.put(
                    {"type": UIEventType.ERROR, "message": "Stopped by user.", "turn_id": turn_id}
                )
                return
            loop_count += 1
            try:
                response = self.llm_connector.chat_with_tools(
                    system_prompt=turn_system_prompt,
                    chat_history=working_history_request,
                    tools=llm_tools,
                    stop_event=self.orchestrator.stop_event,
                )
            except InterruptedError:
                self.ui_queue.put(
                    {"type": UIEventType.ERROR, "message": "Stopped by user.", "turn_id": turn_id}
                )
                return
            except Exception as e:
                if self.orchestrator.stop_event.is_set():
                    return
                raise e

            if not response.content and not response.tool_calls:
                self.logger.warning(f"Empty response from LLM for turn {turn_id}")
                continue

            # We create the message using the actual model response data
            # This is an ASSISTANT message (even if it only contains tool calls or thoughts)
            llm_msg = Message(
                role=MessageRole.ASSISTANT,
                content=response.content,
                thought=response.thought,
                thought_signature=response.thought_signature,
                tool_calls=response.tool_calls,
                turn_id=turn_id,
            )
            working_history.append(llm_msg)
            working_history_request.append(llm_msg)

            # Add the full llm_msg to history, not a stripped one
            session_in_thread.history.append(llm_msg)
            msg_index = len(session_in_thread.history) - 1
            narrative_text += f"\n{response.content}"

            self.ui_queue.put(
                {
                    "type": UIEventType.MESSAGE_BUBBLE,
                    "role": MessageRole.ASSISTANT,
                    "content": response.content,
                    "index": msg_index,
                    "message_data": llm_msg.model_dump(),
                    "turn_id": turn_id,
                }
            )

            if response.tool_calls:
                self.logger.info(
                    f"ReAct Loop {loop_count}: Model called {len(response.tool_calls)} tools."
                )
                if response.thought:
                    self.ui_queue.put(
                        {
                            "type": UIEventType.THOUGHT_BUBBLE,
                            "content": response.thought,
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
                                "pre_fetched_mems": mems if 'mems' in locals() else None,
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
                                role=MessageRole.TOOL,
                                tool_call_id=call_id,
                                name=name,
                                content=json.dumps(res_data, indent=2),
                                turn_id=turn_id,
                            )
                            working_history.append(tool_msg)
                            working_history_request.append(tool_msg)
                            # CRITICAL: Persist tool messages to history!
                            session_in_thread.history.append(tool_msg)
                        except Exception as e:
                            tool_error = Message(
                                role=MessageRole.TOOL,
                                tool_call_id=call_id,
                                name=name,
                                content=json.dumps({"error": str(e)}, indent=2),
                                turn_id=turn_id,
                            )
                            working_history.append(tool_error)
                            working_history_request.append(tool_error)
                            # Persist error result too
                            session_in_thread.history.append(tool_error)
                            self.ui_queue.put(
                                {
                                    "type": UIEventType.TOOL_RESULT,
                                    "name": name,
                                    "result": str(e),
                                    "is_error": True,
                                    "turn_id": turn_id,
                                }
                            )
                    else:
                        tool_error = Message(
                            role=MessageRole.TOOL,
                            tool_call_id=call_id,
                            name=name,
                            content=json.dumps({"error": f"Tool '{name}' not found."}, indent=2),
                            turn_id=turn_id,
                        )
                        working_history.append(tool_error)
                        working_history_request.append(tool_error)
                        session_in_thread.history.append(tool_error)
                continue
            else:
                # No more tools, we are done
                break

        # --- 5B. LOOP EXHAUSTION GUARD ---
        if not narrative_text:
            self.logger.warning(
                f"ReAct loop exhausted without narrative. Forcing narrative generation. Turn ID: {turn_id}"
            )
            # Make one final streaming response call to force a text response
            try:
                fallback_response = self.llm_connector.get_streaming_response(
                    system_prompt=turn_system_prompt,
                    chat_history=working_history_request,
                    stop_event=self.orchestrator.stop_event,
                )
                narrative_text = "".join(fallback_response)
            except InterruptedError:
                return
                if narrative_text:
                    self.ui_queue.put(
                        {
                            "type": UIEventType.MESSAGE_BUBBLE,
                            "role": MessageRole.ASSISTANT,
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
            if not any(m.content == narrative_text for m in final_history if m.role == MessageRole.ASSISTANT):
                 final_history.append(Message(role=MessageRole.ASSISTANT, content=narrative_text))

            final_history.append(
                Message(
                    role=MessageRole.USER,
                    content="Simmulate 3-5 brief, concise, and short responses as if the Player wrote them (E.g. 'I do X', 'I go to Y', 'What is Z?', etc.), based on the narrative above. Return strictly as JSON.",
                )
            )

            # Fast, small schema call
            suggestions_out = self.llm_connector.get_structured_response(
                system_prompt=turn_system_prompt,
                chat_history=final_history,
                output_schema=TurnSuggestions,
                temperature=0.7,
                stop_event=self.orchestrator.stop_event,
            )
            choices = list(suggestions_out.choices or [])

        except Exception as e:
            self.logger.warning(f"Turn suggestions generation failed: {e}")

        # --- 7. PERSISTENCE ---
        # Note: Assistant messages were already added to session_in_thread.history
        # incrementally during the ReAct loop to support live interactivity.

        self.orchestrator._update_game_in_thread(
            game_session, thread_db_manager, session_in_thread
        )

        if choices:
            self.ui_queue.put(
                {
                    "type": UIEventType.CHOICES,
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
            if not any(m.content == narrative_text for m in final_history if m.role == MessageRole.ASSISTANT):
                 final_history.append(Message(role=MessageRole.ASSISTANT, content=narrative_text))

            final_history.append(
                Message(
                    role=MessageRole.USER,
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
                stop_event=self.orchestrator.stop_event,
            )

            # Persist with new DB connection
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
        first_real_role = history[0].role if history else MessageRole.USER
        # Choose opposite role to preserve alternation (user-user / assistant-assistant avoidance)
        prefix_role = MessageRole.ASSISTANT if first_real_role == MessageRole.USER else MessageRole.USER
        prefix = Message(
            role=prefix_role,
            content=f"# STORY SO FAR\n{summary}",
        )
        return [prefix, *history]

    def _get_request_history_with_synthetic_tools(
        self,
        working_history: list[Message],
        synthetic_tool_messages: dict[str, Message],
        turn_id: str,
    ) -> list[Message]:
        """
        Prepares the chat history for the LLM request, injecting synthetic tool results.
        Supports a compatibility mode for models/templates that struggle with strict
        OpenAI tool alternation (Assistant tool_calls -> Tool results).
        """
        if not synthetic_tool_messages:
            return list(working_history)

        compat_mode = os.environ.get("SYNTHETIC_TOOLS_COMPAT_MODE", "false").lower() == "true"
        working_history_request = list(working_history)

        if compat_mode:
            # COMPAT MODE: Append synthetic info to the last USER message
            self.logger.debug("Using SYNTHETIC_TOOLS_COMPAT_MODE: Inlining tools into last User message.")

            # Format synthetic messages into a single block with specific headings
            extra_context = ""
            for tool_id, msg in synthetic_tool_messages.items():
                if tool_id == "passive_rag_context":
                    heading = "RELEVANT CONTEXT (RAG)"
                elif tool_id == "available_tools":
                    heading = "AVAILABLE TOOLS"
                else:
                    heading = f"ADDITIONAL CONTEXT: {tool_id.replace('_', ' ').upper()}"

                extra_context += f"\n\n---\n### {heading}\n{msg.content}\n"

            # Find the last USER message to append to
            user_msg_index = -1
            for i in range(len(working_history_request) - 1, -1, -1):
                if working_history_request[i].role == MessageRole.USER:
                    user_msg_index = i
                    break

            if user_msg_index != -1:
                # Append to existing message
                original_content = working_history_request[user_msg_index].content or ""
                working_history_request[user_msg_index] = working_history_request[user_msg_index].model_copy(
                    update={"content": f"{original_content}{extra_context}"}
                )
            else:
                # No user message? Prepend as a fake USER message instead of crashing
                self.logger.warning("No USER message found for Compat Mode. Prepending as USER message.")
                working_history_request.insert(0, Message(
                    role=MessageRole.USER,
                    content=f"IMPORTANT CONTEXT:{extra_context}",
                    turn_id=turn_id
                ))
        else:
            # STRICT MODE: Follow OpenAI standard (Assistant tool_calls -> Tool results)
            synthetic_tool_calls: list[dict[str, Any]] = [
                {"id": msg.tool_call_id, "name": msg.name or tool_id, "arguments": {}}
                for tool_id, msg in synthetic_tool_messages.items()
            ]

            # Append synthetic assistant message that "called" these tools
            working_history_request.append(Message(
                role=MessageRole.ASSISTANT,
                content=None,
                tool_calls=synthetic_tool_calls,
                turn_id=turn_id,
            ))
            # Append the actual tool results
            working_history_request.extend(synthetic_tool_messages.values())

        return working_history_request


