from __future__ import annotations

import asyncio
import os
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Generator
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
    def __init__(self):
        # Concurrency limit for parallel setup tasks (World/Char Gen)
        self._max_workers = int(os.environ.get("SETUP_MAX_WORKERS", 5))
        self._semaphore: asyncio.Semaphore | None = None
        # Global timeout for any single LLM call (default 5 minutes)
        self.timeout = float(os.environ.get("LLM_TIMEOUT", 300))

    @property
    def semaphore(self) -> asyncio.Semaphore:
        """Lazy initialization of the semaphore to ensure it's bound to the correct event loop."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self._max_workers)
        return self._semaphore

    @semaphore.setter
    def semaphore(self, value: asyncio.Semaphore):
        self._semaphore = value

    # --- Synchronous Interface (for Turn Manager) ---

    def get_streaming_response(
        self, system_prompt: str, chat_history: list[Message]
    ) -> Generator[str, None, None]:
        """Synchronous wrapper for streaming."""
        # Note: Implementation might vary by provider for sync streaming
        loop = asyncio.new_event_loop()
        async_gen = self.async_get_streaming_response(system_prompt, chat_history)
        try:
            while True:
                try:
                    yield loop.run_until_complete(async_gen.__anext__())
                except StopAsyncIteration:
                    break
        finally:
            loop.close()

    def get_structured_response(
        self,
        system_prompt: str,
        chat_history: list[Message],
        output_schema: type[BaseModel],
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> BaseModel:
        """Synchronous wrapper for structured output."""
        return asyncio.run(
            self.async_get_structured_response(
                system_prompt, chat_history, output_schema, temperature, top_p
            )
        )

    def chat_with_tools(
        self,
        system_prompt: str,
        chat_history: list[Message],
        tools: list[dict[str, Any]],
    ) -> LLMResponse:
        """Synchronous wrapper for tool calls."""
        return asyncio.run(
            self.async_chat_with_tools(system_prompt, chat_history, tools)
        )

    # --- Asynchronous Interface (for Parallel Processing) ---

    @abstractmethod
    def async_get_streaming_response(
        self, system_prompt: str, chat_history: list[Message]
    ) -> AsyncGenerator[str, None]:
        pass

    @abstractmethod
    async def async_get_structured_response(
        self,
        system_prompt: str,
        chat_history: list[Message],
        output_schema: type[BaseModel],
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> BaseModel:
        pass

    @abstractmethod
    async def async_chat_with_tools(
        self,
        system_prompt: str,
        chat_history: list[Message],
        tools: list[dict[str, Any]],
    ) -> LLMResponse:
        pass

