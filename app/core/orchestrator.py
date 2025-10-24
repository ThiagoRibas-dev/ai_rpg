import os
from app.gui.main_view import MainView
from app.models.session import Session
from app.models.game_session import GameSession
from app.llm.llm_connector import LLMConnector
from app.llm.gemini_connector import GeminiConnector
from app.llm.openai_connector import OpenAIConnector
from app.tools.registry import ToolRegistry
from app.io.schemas import TurnPlan, NarrativeStep

class Orchestrator:
    def __init__(self, view: MainView, db_manager):
        self.view = view
        self.db_manager = db_manager
        
        self.llm_connector = self._get_llm_connector()
        self.tool_registry = ToolRegistry()

        self.view.orchestrator = self

    def _get_llm_connector(self) -> LLMConnector:
        provider = os.environ.get("LLM_PROVIDER", "GEMINI").upper()
        if provider == "GEMINI":
            return GeminiConnector()
        elif provider == "OPENAI":
            return OpenAIConnector()
        else:
            raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")

    def handle_send(self, session: "GameSession"):
        user_input = self.view.get_input()
        if not user_input:
            return

        self.session.add_message("user", user_input)
        self.view.add_message(f"You: {user_input}\n")
        self.view.clear_input()

        prompt = "\n".join([f"{m.role}: {m.content}" for m in self.session.get_history()])
        tool_schemas = self.tool_registry.get_all_schemas()
        print(f"--- Prompt for Planning ---\n{prompt}\n--------------------------")
        print(f"--- Tools for Planning ---\n{tool_schemas}\n-------------------------")

        # 1. Planning Step
        print("--- 1. Requesting TurnPlan from LLM ---")
        try:
            plan_response = self.llm_connector.get_structured_response(prompt, tool_schemas, TurnPlan)
            print(f"--- LLM Response (TurnPlan) ---\n{plan_response}\n-----------------------------")
            plan = TurnPlan.parse_obj(plan_response)
        except Exception as e:
            print(f"--- ERROR during planning ---\n{e}\n-----------------------------")
            self.view.add_message(f"Error during planning: {e}\n")
            return

        self.view.add_message(f"[Thought: {plan.thought}]\n")

        # 2. Tool Execution Step
        print("--- 2. Executing Tools ---")
        tool_results = []
        if plan.tool_calls:
            for tool_call in plan.tool_calls:
                try:
                    result = self.tool_registry.execute_tool(tool_call.name, tool_call.arguments)
                    tool_results.append({"tool_name": tool_call.name, "result": result})
                    self.view.add_message(f"[Tool: {tool_call.name}({tool_call.arguments}) -> {result}]\n")
                except Exception as e:
                    tool_results.append({"tool_name": tool_call.name, "error": str(e)})
                    self.view.add_message(f"[Tool Error: {tool_call.name} -> {e}]\n")
        print(f"--- Tool Results ---\n{tool_results}\n--------------------")

        # 3. Narrative Generation Step
        narrative_prompt = f"{prompt}\nTool Results: {tool_results}"
        print(f"--- Prompt for Narrative ---\n{narrative_prompt}\n---------------------------")
        print("--- 3. Requesting NarrativeStep from LLM ---")
        try:
            narrative_response = self.llm_connector.get_structured_response(narrative_prompt, [], NarrativeStep)
            print(f"--- LLM Response (NarrativeStep) ---\n{narrative_response}\n----------------------------------")
            narrative_step = NarrativeStep.parse_obj(narrative_response)
        except Exception as e:
            print(f"--- ERROR during narrative generation ---\n{e}\n---------------------------------------")
            self.view.add_message(f"Error during narrative generation: {e}\n")
            return

        self.view.add_message(f"AI: {narrative_step.narrative}\n")
        self.session.add_message("assistant", narrative_step.narrative)

        # TODO: Process state_patch and memory_intent

        self.update_game(session)

    def run(self):
        self.view.mainloop()

    def new_session(self, system_prompt: str):
        self.session = Session("default_session", system_prompt=system_prompt)

    def save_game(self, name: str, prompt_id: int):
        session_data = self.session.to_json()
        self.db_manager.save_session(name, session_data, prompt_id)

    def load_game(self, session_id: int):
        game_session = self.db_manager.load_session(session_id)
        if game_session:
            self.session = Session.from_json(game_session.session_data)

    def update_game(self, session: "GameSession"):
        session.session_data = self.session.to_json()
        self.db_manager.update_session(session)