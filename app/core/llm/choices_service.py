from typing import List
from app.models.message import Message
from app.io.schemas import ActionChoices
from app.llm.llm_connector import LLMConnector

class ChoicesService:
    def __init__(self, llm: LLMConnector):
        self.llm = llm

    def generate(self, context_text: str, chat_history: List[Message]) -> ActionChoices | None:
        try:
            data = self.llm.get_structured_response(
                system_prompt=context_text,
                chat_history=chat_history,
                output_schema=ActionChoices
            )
            return ActionChoices.model_validate(data) if data is not None else None
        except Exception:
            return None
