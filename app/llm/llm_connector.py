from __future__ import annotations

import asyncio
import logging
import os
import threading
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Generator
from dataclasses import dataclass
from typing import Any, cast

from pydantic import BaseModel

from app.models.message import Message

logger = logging.getLogger(__name__)


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
        self,
        system_prompt: str,
        chat_history: list[Message],
        stop_event: threading.Event | None = None,
    ) -> Generator[str, None, None]:
        """Synchronous wrapper for streaming."""
        # Note: Implementation might vary by provider for sync streaming
        loop = asyncio.new_event_loop()
        async_gen = self.async_get_streaming_response(system_prompt, chat_history)
        try:
            while True:
                if stop_event and stop_event.is_set():
                    break
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
        stop_event: threading.Event | None = None,
    ) -> BaseModel:
        """Synchronous wrapper for structured output."""
        return cast(
            BaseModel,
            asyncio.run(
                self._run_with_interrupt(
                    self.async_get_structured_response(
                        system_prompt, chat_history, output_schema, temperature, top_p
                    ),
                    stop_event,
                )
            ),
        )

    def chat_with_tools(
        self,
        system_prompt: str,
        chat_history: list[Message],
        tools: list[dict[str, Any]],
        stop_event: threading.Event | None = None,
    ) -> LLMResponse:
        """Synchronous wrapper for tool calls."""
        return cast(
            LLMResponse,
            asyncio.run(
                self._run_with_interrupt(
                    self.async_chat_with_tools(system_prompt, chat_history, tools),
                    stop_event,
                )
            ),
        )

    async def _run_with_interrupt(
        self, coro, stop_event: threading.Event | None
    ) -> Any:
        """Helper to run a coroutine until either it completes or the stop_event is set."""
        if not stop_event:
            return await coro

        work_task = asyncio.create_task(coro)

        async def _wait_for_stop():
            while not stop_event.is_set():
                await asyncio.sleep(0.2)
            return "stopped"

        stop_task = asyncio.create_task(_wait_for_stop())

        done, pending = await asyncio.wait(
            [work_task, stop_task], return_when=asyncio.FIRST_COMPLETED
        )

        for task in pending:
            task.cancel()

        if work_task in done:
            return work_task.result()
        else:
            logger.info("🛑 LLM call interrupted by stop signal.")
            raise InterruptedError("Stopped by user")

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

