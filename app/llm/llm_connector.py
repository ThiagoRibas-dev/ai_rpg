from abc import ABC, abstractmethod
from typing import Generator, Type, List, Dict, Any, Optional
from pydantic import BaseModel
from app.models.message import Message
from dataclasses import dataclass

@dataclass
class LLMResponse:
    content: Optional[str]
    tool_calls: Optional[List[Dict[str, Any]]]



class LLMConnector(ABC):
    @abstractmethod
    def get_streaming_response(
        self, system_prompt: str, chat_history: List[Message]
    ) -> Generator[str, None, None]:
        pass

    @abstractmethod
    def get_structured_response(
        self,
        system_prompt: str,
        chat_history: List[Message],
        output_schema: Type[BaseModel],
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> BaseModel:
        pass

    @abstractmethod
    def get_tool_calls(
        self,
        system_prompt: str,
        chat_history: List[Message],
        tools: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Makes an API call and returns a list of tool calls requested by the model."""
        pass

    @abstractmethod
    def chat_with_tools(
        self,
        system_prompt: str,
        chat_history: List[Message],
        tools: List[Dict[str, Any]],
    ) -> LLMResponse:
        pass
