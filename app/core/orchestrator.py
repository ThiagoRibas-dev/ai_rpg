import os
from app.gui.main_view import MainView
from app.models.session import Session
from app.llm.llm_connector import LLMConnector
from app.llm.gemini_connector import GeminiConnector
from app.llm.openai_connector import OpenAIConnector

class Orchestrator:
    def __init__(self, view: MainView):
        self.view = view
        
        # Load the initial prompt
        with open("prompts/default.txt", "r") as f:
            system_prompt = f.read()

        self.session = Session("default_session", system_prompt=system_prompt)
        self.llm_connector = self._get_llm_connector()

        self.view.send_button.configure(command=self.handle_send)

    def _get_llm_connector(self) -> LLMConnector:
        provider = os.environ.get("LLM_PROVIDER", "GEMINI").upper()
        if provider == "GEMINI":
            return GeminiConnector()
        elif provider == "OPENAI":
            return OpenAIConnector()
        else:
            raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")

    def handle_send(self):
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

    def run(self):
        self.view.mainloop()