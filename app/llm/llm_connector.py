from abc import ABC, abstractmethod
from typing import Generator, Dict, Any, Type
from pydantic import BaseModel

class LLMConnector(ABC):
    @abstractmethod
    def get_streaming_response(self, prompt: str) -> Generator[str, None, None]:
        pass

    @abstractmethod
    def get_structured_response(self, prompt: str, output_schema: Type[BaseModel]) -> Dict[str, Any]:
        pass