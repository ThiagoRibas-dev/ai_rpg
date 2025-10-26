import os
import json
import logging
from typing import Callable, Dict, Any, List
from app.gui.main_view import MainView
from app.models.session import Session
from app.models.game_session import GameSession
from app.llm.llm_connector import LLMConnector
from app.llm.gemini_connector import GeminiConnector
from app.llm.openai_connector import OpenAIConnector
from app.tools.registry import ToolRegistry
from app.io.schemas import TurnPlan, NarrativeStep

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

PLAN_TEMPLATE = """You are a roleplay engine. Your goal is to select and execute the most appropriate tools to respond to the user's input and advance the game state.
Available tools (JSON Schemas):
{tool_schemas}

Recent chat:
{chat}
"""

NARRATIVE_TEMPLATE = """You are a roleplay engine. Write the next scene based on tool results.
Return a JSON object strictly matching the NarrativeStep schema.
Guidelines:
- Use second person ("You ...").
- Respect tool outcomes; do not fabricate mechanics.
- Propose minimal patches and appropriate memory intents.

Recent chat:
{chat}

Tool results:
{tool_results}
"""

class Orchestrator:
    def __init__(self, view: MainView, db_manager):
        self.view = view
        self.db_manager = db_manager
        self.tool_event_callback: Callable[[str], None] | None = None
        self.llm_connector = self._get_llm_connector()
        self.tool_registry = ToolRegistry()
        self.view.orchestrator = self
        self.session: Session | None = None

    def _get_llm_connector(self) -> LLMConnector:
        provider = os.environ.get("LLM_PROVIDER", "GEMINI").upper()
        if provider == "GEMINI":
            return GeminiConnector()
        elif provider == "OPENAI":
            return OpenAIConnector()
        else:
            raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")

    def plan_and_execute(self, session: "GameSession"):
        logger.debug("Starting plan_and_execute")
        user_input = self.view.get_input()
        if not user_input or not self.session:
            logger.debug("No user input or session found, returning.")
            return

        self.session.add_message("user", user_input)
        self.view.add_message(f"You: {user_input}\n")
        self.view.clear_input()

        chat_history = self.session.get_history()
        chat_str = "\n".join([f"{msg.role}: {msg.content}" for msg in chat_history])

        # 1) Plan
        try:
            prompt = PLAN_TEMPLATE.format(
                tool_schemas=self.tool_registry.get_all_schemas(),
                chat=chat_str
            )
            plan_dict = self.llm_connector.get_structured_response(
                prompt=prompt,
                output_schema=TurnPlan
            )
            plan = TurnPlan.model_validate(plan_dict)
            self.view.add_message(f"[Thought: {plan.thought}]\n")
        except Exception as e:
            logger.error(f"Error during planning: {e}", exc_info=True)
            self.view.add_message(f"Error during planning: {e}\n")
            return

        # 2) Execute tools
        tool_results: List[Dict[str, Any]] = []
        if plan.tool_calls:
            for call in plan.tool_calls:
                try:
                    tool_name = call.name
                    # The model returns a JSON string for arguments, so we parse it.
                    # Handle optional arguments, defaulting to an empty JSON object string.
                    tool_args_str = call.arguments or "{}"
                    tool_args = json.loads(tool_args_str)
                    self.view.add_message(f"[Tool: {tool_name}({tool_args})]\n")
                    result = self.tool_registry.execute_tool(tool_name, tool_args)
                    tool_results.append({"tool_name": tool_name, "arguments": tool_args, "result": result})
                    self.view.add_message(f"[Result: {result}]\n")
                except Exception as e:
                    logger.error(f"Error executing tool {tool_name}: {e}")
                    tool_results.append({"tool_name": tool_name, "arguments": call.arguments, "error": str(e)})
                    self.view.add_message(f"[Error: {e}]\n")

        # 3) Narrative + proposals
        try:
            tool_results_str = str(tool_results)
            prompt = NARRATIVE_TEMPLATE.format(
                chat=chat_str,
                tool_results=tool_results_str
            )
            narrative_dict = self.llm_connector.get_structured_response(
                prompt=prompt,
                output_schema=NarrativeStep
            )
            narrative = NarrativeStep.model_validate(narrative_dict)
        except Exception as e:
            logger.error(f"Error during narrative generation: {e}", exc_info=True)
            self.view.add_message(f"Error during narrative: {e}\n")
            return

        self.view.add_message(f"AI: {narrative.narrative}\n")
        self.session.add_message("assistant", narrative.narrative)

        # 4) Apply patches and memories via tools (MVP handlers are in-memory)
        if narrative.proposed_patches:
            for patch in narrative.proposed_patches:
                try:
                    args = {"entity_type": patch.entity_type, "key": patch.key, "patch": [op.model_dump() for op in patch.ops]}
                    result = self.tool_registry.execute_tool("state.apply_patch", args)
                    if self.tool_event_callback:
                        self.tool_event_callback(f"state.apply_patch ✓ -> {result}")
                except Exception as e:
                    self.view.add_message(f"[Patch Error: {patch.key} -> {e}]\n")

        if narrative.memory_intents:
            for mem in narrative.memory_intents:
                try:
                    args = {"kind": mem.kind, "content": mem.content}
                    if mem.priority is not None:
                        args["priority"] = mem.priority
                    if mem.tags is not None:
                        args["tags"] = mem.tags
                    result = self.tool_registry.execute_tool("memory.upsert", args)
                    if self.tool_event_callback:
                        self.tool_event_callback(f"memory.upsert ✓ -> {result}")
                except Exception as e:
                    self.view.add_message(f"[Memory Error: {mem.content[:32]}... -> {e}]\n")

        # Persist session JSON with any changes (MVP: just the chat history)
        self.update_game(session)

    def run(self):
        self.view.mainloop()

    def new_session(self, system_prompt: str):
        self.session = Session("default_session", system_prompt=system_prompt)

    def save_game(self, name: str, prompt_id: int):
        if not self.session:
            return
        session_data = self.session.to_json()
        self.db_manager.save_session(name, session_data, prompt_id)

    def load_game(self, session_id: int):
        game_session = self.db_manager.load_session(session_id)
        if game_session:
            self.session = Session.from_json(game_session.session_data)

    def update_game(self, session: "GameSession"):
        if not self.session:
            return
        session.session_data = self.session.to_json()
        self.db_manager.update_session(session)