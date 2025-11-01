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
from app.io.schemas import TurnPlan, NarrativeStep, ActionChoices
from app.models.message import Message

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

MAX_HISTORY_MESSAGES = 20

PLAN_TEMPLATE = """You are a roleplay engine. Your goal is to select and execute the most appropriate tools to respond to the user's input and advance the game state.
Available tools (JSON Schemas):
{tool_schemas}
"""

NARRATIVE_TEMPLATE = """You are a roleplay engine. Write the next scene based on the Planner's Intent and the tool results.
Return a JSON object strictly matching the NarrativeStep schema.

The Planner's Intent (your high-level goal for this turn):
{planner_thought}

Guidelines:
- Your narration must align with the Planner's Intent.
- Use second person ("You ...").
- Respect tool outcomes; do not fabricate mechanics. If tool results are empty, rely primarily on the Planner's Intent.
- Propose minimal patches and appropriate memory intents.

Tool results:
{tool_results}
"""

CHOICE_GENERATION_TEMPLATE = """Based on the current game state and the narrative you just presented, generate exactly 3 concise action choices for the player.

Each choice should be:
- A short, actionable statement (preferably under 10 words)
- Something the player can say or do
- Relevant to the current situation
- Distinct from the other choices

Guidelines:
- Think about what makes sense given the narrative context
- Offer diverse options (e.g., combat, diplomacy, investigation)
- Keep choices clear and direct

Recent narrative context:
{narrative}
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

    def _get_truncated_history(self) -> List[Message]:
        """
        Returns a truncated copy of the session history, preserving the system prompt.
        """
        if not self.session:
            return []
        
        full_history = self.session.get_history()
        if len(full_history) <= MAX_HISTORY_MESSAGES:
            return full_history

        # Preserve the first message (system prompt) and take the last X messages.
        system_prompt = full_history[0]
        recent_messages = full_history[-(MAX_HISTORY_MESSAGES - 1):]
        
        return [system_prompt] + recent_messages

    def _assemble_context(self, base_template: str, session: GameSession) -> str:
        """
        Assembles the final system prompt by combining Memory, World Info, base template, and Author's Note.
        """
        parts = []

        # 1. Memory
        if session.memory and session.memory.strip():
            parts.append(f"=== MEMORY ===\n{session.memory.strip()}\n")

        # 2. World Info (keyword matching)
        if session.prompt_id:
            world_infos = self.db_manager.get_world_info_by_prompt(session.prompt_id)
            triggered_infos = []
            
            # Get recent user messages to check for keyword triggers
            recent_history = self._get_truncated_history()
            recent_text = " ".join([msg.content for msg in recent_history[-5:]])  # Last 5 messages
            
            for wi in world_infos:
                keywords = [k.strip().lower() for k in wi.keywords.split(",")]
                if any(keyword in recent_text.lower() for keyword in keywords):
                    triggered_infos.append(wi.content)
            
            if triggered_infos:
                parts.append("=== WORLD INFO ===\n" + "\n\n".join(triggered_infos) + "\n")

        # 3. Base template
        parts.append(f"=== INSTRUCTIONS ===\n{base_template}\n")

        # 4. Author's Note
        if session.authors_note and session.authors_note.strip():
            parts.append(f"=== AUTHOR'S NOTE ===\n{session.authors_note.strip()}\n")

        return "\n".join(parts)

    def plan_and_execute(self, session: GameSession):
        logger.debug("Starting plan_and_execute")
        user_input = self.view.get_input()
        if not user_input or not self.session:
            logger.debug("No user input or session found, returning.")
            return

        self.session.add_message("user", user_input)
        self.view.add_message(f"You: {user_input}\n")
        self.view.clear_input()

        # 1) Plan
        try:
            base_plan_template = PLAN_TEMPLATE.format(
                tool_schemas=self.tool_registry.get_all_schemas()
            )
            system_prompt_plan = self._assemble_context(base_plan_template, session)
            
            chat_history = self._get_truncated_history()
            plan_dict = self.llm_connector.get_structured_response(
                system_prompt=system_prompt_plan,
                chat_history=chat_history,
                output_schema=TurnPlan
            )
            plan = TurnPlan.model_validate(plan_dict)
            self.view.add_message(f"\n[Thought: {plan.thought}]\n\n")
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
            base_narrative_template = NARRATIVE_TEMPLATE.format(
                planner_thought=plan.thought,
                tool_results=tool_results_str
            )
            system_prompt_narrative = self._assemble_context(base_narrative_template, session)
            
            chat_history = self._get_truncated_history()
            narrative_dict = self.llm_connector.get_structured_response(
                system_prompt=system_prompt_narrative,
                chat_history=chat_history,
                output_schema=NarrativeStep
            )
            narrative = NarrativeStep.model_validate(narrative_dict)
        except Exception as e:
            logger.error(f"Error during narrative generation: {e}", exc_info=True)
            self.view.add_message(f"Error during narrative: {e}\n")
            return

        self.view.add_message(f"AI: {narrative.narrative}\n")
        self.session.add_message("assistant", narrative.narrative)

        # 4) Apply patches and memories
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

        # 5) Generate action choices
        try:
            choice_template = CHOICE_GENERATION_TEMPLATE.format(
                narrative=narrative.narrative
            )
            system_prompt_choices = self._assemble_context(choice_template, session)
            
            chat_history = self._get_truncated_history()
            choices_dict = self.llm_connector.get_structured_response(
                system_prompt=system_prompt_choices,
                chat_history=chat_history,
                output_schema=ActionChoices
            )
            action_choices = ActionChoices.model_validate(choices_dict)
            
            # Display the choices in the UI
            self.view.display_action_choices(action_choices.choices)
        except Exception as e:
            logger.error(f"Error generating action choices: {e}", exc_info=True)
            # Don't fail the whole turn if choice generation fails
            self.view.add_message(f"[Choice generation failed: {e}]\n")

        # Persist session
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

    def update_game(self, session: GameSession):
        if not self.session:
            return
        session.session_data = self.session.to_json()
        self.db_manager.update_session(session)