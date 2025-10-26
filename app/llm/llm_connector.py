from abc import ABC, abstractmethod
from typing import Generator, Dict, Any, Type, List
from pydantic import BaseModel
from app.models.message import Message

class LLMConnector(ABC):
    @abstractmethod
    def get_streaming_response(self, system_prompt: str, chat_history: List[Message]) -> Generator[str, None, None]:
        pass

    @abstractmethod
    def get_structured_response(self, system_prompt: str, chat_history: List[Message], output_schema: Type[BaseModel]) -> Dict[str, Any]:
        pass
