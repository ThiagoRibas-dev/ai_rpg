from abc import ABC, abstractmethod
from typing import Generator, List, Dict, Any, Type
from pydantic import BaseModel

class LLMConnector(ABC):
    """
    Abstract base class for LLM connectors.
    """

    @abstractmethod
    def get_streaming_response(self, prompt: str) -> Generator[str, None, None]:
        """
        Yields a stream of string responses from the LLM.
        """
        pass

    @abstractmethod
    def get_structured_response(self, prompt: str, tools: List[Dict[str, Any]], output_schema: Type[BaseModel]) -> Dict[str, Any]:
        """
        Returns a structured JSON response from the LLM that conforms to the
        provided Pydantic schema.
        """
        pass