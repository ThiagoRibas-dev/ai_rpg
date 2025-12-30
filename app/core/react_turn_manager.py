import uuid
import json
import logging
from typing import Dict, Type
from pydantic import BaseModel
from app.context.context_builder import ContextBuilder
from app.context.memory_retriever import MemoryRetriever
from app.context.state_context import StateContextBuilder
from app.core.metadata.turn_metadata_service import TurnMetadataService
from app.core.simulation_service import SimulationService
from app.models.game_session import GameSession
from app.models.message import Message
from app.models.session import Session
from app.setup.setup_manifest import SetupManifest
from app.tools.executor import ToolExecutor
from app.tools.schemas import Adjust, Set, Mark, Roll, Move, Note
from app.llm.schemas import ActionChoices, TurnSummaryOutput

logger = logging.getLogger(__name__)

MAX_HISTORY_MESSAGES = 50
MAX_REACT_LOOPS = 5


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
        # If manifest is not loaded/valid, raises error
        if not manifest:
            raise ValueError(f"Manifest not found for session {game_session.id}")
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
            self.logger,
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
        dynamic_context = context_builder.build_dynamic_context(
            game_session, chat_history
        )
        turn_system_prompt = f"{static_instruction}\n\n{dynamic_context}"
        working_history = list(chat_history)
        # Prepend rolling summary as one message (role chosen to preserve alternation)
        working_history = self._prepend_rolling_summary(game_session, working_history)
        # Injects RAG as tool result messages (protocol-correct)
        working_history = self._inject_rag_as_tool_result(
            game_session=game_session,
            session_in_thread=session_in_thread,
            mem_retriever=mem_retriever,
            history=working_history,
            turn_id=turn_id,
            kinds=["episodic", "lore", "semantic", "rule"],
            limit=8,
        )
        # --- 4. TOOL INJECTION ---
        active_tool_names = [
            Adjust.model_fields["name"].default,
            Set.model_fields["name"].default,
            Mark.model_fields["name"].default,
            Roll.model_fields["name"].default,
            Move.model_fields["name"].default,
            Note.model_fields["name"].default,
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
        # --- 5. ACTION LOOP ---
        loop_count = 0
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
                tool_calls=response.tool_calls,
            )
            working_history.append(assistant_msg)
            self.ui_queue.put(
                {
                    "type": "message_bubble",
                    "role": "assistant",
                    "content": response.content,
                    "turn_id": turn_id,
                }
            )
            if response.tool_calls:
                self.logger.info(
                    f"ReAct Loop {loop_count}: Model called {len(response.tool_calls)} tools."
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
                                content=json.dumps(res_data),
                            )
                            working_history.append(tool_msg)
                        except Exception as e:
                            error_msg = Message(
                                role="tool",
                                tool_call_id=call_id,
                                name=name,
                                content=json.dumps({"error": str(e)}),
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
                            content=json.dumps({"error": f"Tool '{name}' not found."}),
                        )
                        working_history.append(error_msg)
                continue
            else:
                break
        # --- 6. FINAL OUTPUT (STRUCTURED: narrative + choices) ---
        if self.orchestrator.stop_event.is_set():
            return
        narrative_text = ""
        choices = []
        try:
            final_history = list(working_history)
            final_history.append(
                Message(
                    role="user",
                    content=(
                        "Out-of-character: write between 3 and 5 suggestions of actions the Player could take next. Example: \"do X\", \"go to Y\", \"inspect A\", etc."
                    ),
                )
            )
            final_out = self.llm_connector.get_structured_response(
                system_prompt=turn_system_prompt,
                chat_history=final_history,
                output_schema=ActionChoices,
                temperature=0.7,
            )
            choices = list(final_out.choices or [])
        except Exception as e:
            self.logger.warning(f"Final structured output failed: {e}")
        
        if self.orchestrator.stop_event.is_set():
            return

        if choices:
            self.ui_queue.put(
                {
                    "type": "choices",
                    "choices": choices,
                    "turn_id": turn_id,
                }
            )
        # --- 7. TURN METADATA (STRUCTURED: summary/tags/importance) ---
        turn_summary = ""
        turn_tags = []
        turn_importance = 3
        if narrative_text and not self.orchestrator.stop_event.is_set():
            try:
                meta_history = list(working_history)
                meta_history.append(Message(role="assistant", content=narrative_text))
                meta_history.append(
                    Message(
                        role="user",
                        content=(
                            "Out-of-character: summarize this turn for retrieval and performance. "
                            "Return JSON only with: summary, tags, importance."
                        ),
                    )
                )
                meta = self.llm_connector.get_structured_response(
                    system_prompt=turn_system_prompt,
                    chat_history=meta_history,
                    output_schema=TurnSummaryOutput,
                    temperature=0.2,
                )
                turn_summary = (meta.summary or "").strip()
                # Keep tags sane even if model returns junk
                if meta.tags:
                    turn_tags = [
                        t.strip() for t in meta.tags if isinstance(t, str) and t.strip()
                    ]
                turn_importance = int(meta.importance)
            except Exception as e:
                self.logger.warning(f"Turn metadata generation failed: {e}")
        # --- 8. PERSISTENCE ---
        if narrative_text.strip():
            session_in_thread.add_message("assistant", narrative_text)
        self.orchestrator._update_game_in_thread(
            game_session, thread_db_manager, session_in_thread
        )
        if narrative_text.strip():
            turnmeta = TurnMetadataService(thread_db_manager, self.vector_store)
            turnmeta.persist(
                session_id=game_session.id,
                prompt_id=game_session.prompt_id,
                round_number=len(session_in_thread.get_history()) // 2,
                summary=turn_summary,
                tags=turn_tags,
                importance=turn_importance,
            )

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

    def _inject_rag_as_tool_result(
        self,
        game_session: GameSession,
        session_in_thread: Session,
        mem_retriever: MemoryRetriever,
        history: list[Message],
        turn_id: str,
        kinds: list[str] | None = None,
        limit: int = 8,
    ) -> list[Message]:
        """
        Represents retrieval as a tool call + tool result in the message stream.
        We DO NOT persist these messages; they exist only for the LLM call.
        """
        if not history:
            return history
        # Find last user message (usually the current turn input)
        last_user = None
        for m in reversed(history):
            if m.role == "user" and (m.content or "").strip():
                last_user = m
                break
        if not last_user:
            return history
        # Run retrieval in Python (using your existing retriever)
        # IMPORTANT: do this BEFORE we append tool messages (so retriever still sees last message as user if it expects that)
        kinds = kinds or ["episodic", "semantic", "lore", "rule"]
        mems = mem_retriever.get_relevant(
            session_in_thread,
            recent_messages=history,  # uses last AI + last user to form query
            kinds=kinds,
            limit=limit,
        )
        if not mems:
            return history
        rag_text = mem_retriever.format_for_prompt(mems, title="RETRIEVED CONTEXT")
        payload = {
            "ui": "rag_context",
            "text": rag_text,
            "memory_ids": [m.id for m in mems],
            "kinds": kinds,
        }
        call_id = "call_rag_" + uuid.uuid4().hex
        # Synthetic assistant tool-call message
        synthetic_toolcall = Message(
            role="assistant",
            content="",  # keep empty; avoid leaking into narrative
            tool_calls=[
                {
                    "id": call_id,
                    "name": "context.retrieve",
                    "arguments": {
                        "query": last_user.content[-500:],  # just for traceability
                        "kinds": kinds,
                        "limit": limit,
                    },
                }
            ],
        )
        # Synthetic tool result message
        synthetic_toolresult = Message(
            role="tool",
            tool_call_id=call_id,
            name="context.retrieve",
            content=json.dumps(payload),
        )
        # Insert them at the end (right after last user, since last user is usually the last message here)
        # If you want to be stricter: insert immediately after the located last_user index.
        return history + [synthetic_toolcall, synthetic_toolresult]
