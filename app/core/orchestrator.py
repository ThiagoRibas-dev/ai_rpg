import os
from app.gui.main_view import MainView
from app.models.session import Session
from app.models.game_session import GameSession
from app.llm.llm_connector import LLMConnector
from app.llm.gemini_connector import GeminiConnector
from app.llm.openai_connector import OpenAIConnector

class Orchestrator:
    def __init__(self, view: MainView, db_manager):
        self.view = view
        self.db_manager = db_manager
        
        self.llm_connector = self._get_llm_connector()

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

        # A more sophisticated approach would be to format the whole history.
        prompt = "\n".join([f"{m.role}: {m.content}" for m in self.session.get_history()])

        full_response = ""
        self.view.add_message("AI: ")
        for chunk in self.llm_connector.get_streaming_response(prompt):
            full_response += chunk
            self.view.add_message(chunk)
        
        self.session.add_message("assistant", full_response)
        self.view.add_message("\n")

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