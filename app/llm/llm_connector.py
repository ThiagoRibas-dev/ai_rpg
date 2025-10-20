from abc import ABC, abstractmethod
from typing import Generator

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