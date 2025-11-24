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
from app.tools.schemas import EntityUpdate, GameLog, GameRoll, TimeAdvance, WorldTravel

logger = logging.getLogger(__name__)

MAX_HISTORY_MESSAGES = 50
TOOL_BUDGET_PER_TURN = 10
MAX_REACT_LOOPS = 5


class ReActTurnManager:
    """
    Executes a game turn using an Iterative ReAct (Reason + Act) Loop.
    Optimized for local models (Llama 3, Mistral) and strict API compliance.
    """

    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.logger = orchestrator.logger
        self.llm_connector = orchestrator.llm_connector
        self.tool_registry = orchestrator.tool_registry
        self.vector_store = orchestrator.vector_store
        self.ui_queue = orchestrator.ui_queue

        # Map tool names to Pydantic classes for hydration
        self.tool_map: Dict[str, Type[BaseModel]] = {
            t.model_fields["name"].default: t
            for t in self.tool_registry.get_all_tool_types()
        }

    def execute_turn(self, game_session: GameSession, thread_db_manager):
        """
        Main ReAct Loop:
        1. Build Context
        2. Phase A: Action Loop (Thought -> Tool -> Result)
        3. Phase B: Narrative Generation
        """
        # --- Setup Services with Thread-Local DB ---
        state_builder = StateContextBuilder(
            self.tool_registry, thread_db_manager, self.logger
        )
        mem_retriever = MemoryRetriever(
            thread_db_manager, self.vector_store, self.logger
        )
        sim_service = SimulationService(self.llm_connector, self.logger)
        context_builder = ContextBuilder(
            thread_db_manager,
            self.vector_store,
            state_builder,
            mem_retriever,
            sim_service,
            self.logger,
        )
        executor = ToolExecutor(
            self.tool_registry,
            thread_db_manager,
            self.vector_store,
            self.ui_queue,
            self.logger,
        )
        manifest_mgr = SetupManifest(thread_db_manager)
        manifest = manifest_mgr.get_manifest(game_session.id)

        # --- 1. Context Building ---
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

        # Construct Working Memory (Augmented User Prompt Strategy)
        working_history = list(chat_history)

        # Inject Context into the LAST User message to avoid "System-in-Middle" issues
        if working_history and working_history[-1].role == "user":
            last_msg = working_history[-1]
            augmented_content = (
                f"### CURRENT STATE & CONTEXT ###\n"
                f"{dynamic_context}\n\n"
                f"### PLAYER ACTION ###\n"
                f"{last_msg.content}"
            )
            working_history[-1] = Message(role="user", content=augmented_content)
        else:
            # Fallback if no user message found
            working_history.append(
                Message(
                    role="user", content=f"### CURRENT STATE ###\n{dynamic_context}"
                )
            )

        # Define the "Super Tools"
        active_tool_names = [
            EntityUpdate.model_fields["name"].default,
            GameRoll.model_fields["name"].default,
            WorldTravel.model_fields["name"].default,
            GameLog.model_fields["name"].default,
            TimeAdvance.model_fields["name"].default,
        ]
        llm_tools = self.tool_registry.get_llm_tool_schemas(active_tool_names)

        # --- 2. Phase A: The Action Loop ---
        self.ui_queue.put({"type": "planning_started", "content": "Thinking..."})

        loop_count = 0
        final_narrative = ""

        while loop_count < MAX_REACT_LOOPS:
            loop_count += 1

            # API Call
            response = self.llm_connector.chat_with_tools(
                system_prompt=static_instruction,
                chat_history=working_history,
                tools=llm_tools,
            )

            # 1. Append the ASSISTANT's message to history
            assistant_msg = Message(
                role="assistant",
                content=response.content,
                tool_calls=response.tool_calls,
            )
            working_history.append(assistant_msg)

            # CASE 1: The model wants to use Tools
            if response.tool_calls:
                self.logger.info(
                    f"ReAct Loop {loop_count}: Model called {len(response.tool_calls)} tools."
                )

                # If there is text alongside the tool, it is a THOUGHT (Yellow)
                if response.content:
                    self.ui_queue.put(
                        {"type": "thought_bubble", "content": response.content}
                    )

                for call_data in response.tool_calls:
                    # OpenAI/Llama.cpp returns an 'id'. Gemini doesn't (we handle that in connector).
                    call_id = call_data.get("id", "call_default")
                    name = call_data["name"]
                    args = call_data["arguments"]

                    # Execute Python Logic
                    if name in self.tool_map:
                        try:
                            pydantic_model = self.tool_map[name](**args)

                            # Run Tool (Using executor and manifest!)
                            extra_ctx = {"simulation_service": sim_service}

                            result, _ = executor.execute(
                                [pydantic_model],
                                game_session,
                                manifest,
                                1,
                                current_game_time=game_session.game_time,
                                extra_context=extra_ctx,
                            )

                            # Extract result data
                            res_data = (
                                result[0]["result"]
                                if result
                                else {"error": "No result"}
                            )

                            # 2. Append the TOOL RESULT to history (Strict Protocol)
                            tool_msg = Message(
                                role="tool",
                                tool_call_id=call_id,
                                name=name,
                                content=json.dumps(res_data),
                            )
                            working_history.append(tool_msg)

                        except Exception as e:
                            # Handle execution error gracefully
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
                                }
                            )

                    else:
                        # Handle unknown tool error
                        error_msg = Message(
                            role="tool",
                            tool_call_id=call_id,
                            name=name,
                            content=json.dumps({"error": f"Tool '{name}' not found."}),
                        )
                        working_history.append(error_msg)

                # Continue the loop to let the model react to the tool results
                continue

            # CASE 2: The model did NOT call tools. It is done.
            else:
                # The text it produced is the FINAL NARRATIVE (Green)
                if response.content:
                    final_narrative = response.content

                # Break the Action Loop
                break

        # --- 3. Phase B: Narrative Handling ---
        # If we already got the narrative from the last loop step, use it.
        if final_narrative:
            self.ui_queue.put(
                {
                    "type": "message_bubble",
                    "role": "assistant",
                    "content": final_narrative,
                }
            )
            full_response = final_narrative

        else:
            # Fallback: Force a final narrative generation if the loop ended without text
            working_history.append(
                Message(
                    role="user",
                    content="[System: Actions resolved. Now write the narrative response to the player.]",
                )
            )

            stream = self.llm_connector.get_streaming_response(
                system_prompt=static_instruction, chat_history=working_history
            )

            full_response = ""
            for chunk in stream:
                full_response += chunk

            if full_response.strip():
                self.ui_queue.put(
                    {
                        "type": "message_bubble",
                        "role": "assistant",
                        "content": full_response,
                    }
                )

        # --- 4. Cleanup & Persistence ---
        # Save the FINAL narrative to the session
        if full_response.strip():
            session_in_thread.add_message("assistant", full_response)

        self.orchestrator._update_game_in_thread(
            game_session, thread_db_manager, session_in_thread
        )

        # Turn Metadata
        turnmeta = TurnMetadataService(thread_db_manager, self.vector_store)
        turnmeta.persist(
            session_id=game_session.id,
            prompt_id=game_session.prompt_id,
            round_number=len(session_in_thread.get_history()) // 2,
            summary=full_response[:100] + "...",
            tags=["react_turn"],
            importance=3,
        )
