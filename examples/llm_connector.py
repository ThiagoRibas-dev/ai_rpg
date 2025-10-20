import os
import logging
from typing import Optional
from app.llm.gemini_connector import GeminiConnector
from app.llm.openai_connector import OpenAIConnector
from app.schemas.wrapper_schemas import DualResponse
from app.schemas.action_request import ActionRequest

# Set to logging.DEBUG to see underlying API responses if SDK is modified to not crash
logging.basicConfig(level=logging.DEBUG)


class LLMConnector:
    """
    A class to dispatch LLM calls to either Gemini or OpenAI-compatible APIs.
    """

    def __init__(self):
        llm_provider = os.environ.get("LLM_PROVIDER", "GEMINI").upper()

        if llm_provider == "GEMINI":
            self.active_connector = GeminiConnector()
        elif llm_provider == "OPENAI":
            self.active_connector = OpenAIConnector()
        else:
            raise ValueError(f"Unsupported LLM_PROVIDER: {llm_provider}. Must be 'GEMINI' or 'OPENAI'.")

    def generate_structured_response(
        self,
        action_request: ActionRequest,
        max_retries: int = 3,
        retry_prompt: Optional[str] = None
    ) -> DualResponse:
        return self.active_connector.generate_structured_response(
            action_request=action_request,
            max_retries=max_retries,
            retry_prompt=retry_prompt
        )

    def generate_chat_response(self, action_request: ActionRequest) -> str:
        return self.active_connector.generate_chat_response(action_request=action_request)