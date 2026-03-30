from abc import ABC, abstractmethod
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from app.models.message import Message


@dataclass
class LLMResponse:
    content: str | None
    tool_calls: list[dict[str, Any]] | None
    thought: str | None = None
    thought_signature: str | None = None



class LLMConnector(ABC):
    @abstractmethod
    def get_streaming_response(
        self, system_prompt: str, chat_history: list[Message]
    ) -> Generator[str, None, None]:
        pass

    @abstractmethod
    def get_structured_response(
        self,
        system_prompt: str,
        chat_history: list[Message],
        output_schema: type[BaseModel],
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> BaseModel:
        pass

    @abstractmethod
    def chat_with_tools(
        self,
        system_prompt: str,
        chat_history: list[Message],
        tools: list[dict[str, Any]],
    ) -> LLMResponse:
        pass
