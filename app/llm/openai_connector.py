from __future__ import annotations

import asyncio
import json
import logging
import os
import weakref
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any, cast

import openai
from pydantic import BaseModel, ValidationError

import httpx
from app.llm.llm_connector import LLMConnector, LLMResponse
from app.models.message import Message
from app.models.vocabulary import MessageRole

if TYPE_CHECKING:
    from openai.types.chat import (
        ChatCompletion,
        ChatCompletionAssistantMessageParam,
        ChatCompletionChunk,
        ChatCompletionMessageParam,
        ChatCompletionMessageToolCallParam,
        ChatCompletionSystemMessageParam,
        ChatCompletionToolMessageParam,
        ChatCompletionUserMessageParam,
    )

    class OpenAIToolMessageParam(ChatCompletionToolMessageParam, total=False):
        name: str


logger = logging.getLogger(__name__)


class OpenAIConnector(LLMConnector):
    """
    Reference : https://deepwiki.com/openai/openai-python/4.1-chat-completions-api
    """

    def __init__(self):
        super().__init__()
        self.base_url = os.environ.get("OPENAI_API_BASE_URL")
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.model = os.environ.get("OPENAI_API_MODEL")
        if not self.base_url:
            logger.error("OPENAI_API_BASE_URL environment variable not set.")
            raise ValueError("OPENAI_API_BASE_URL environment variable not set.")
        if not self.api_key:
            logger.error("OPENAI_API_KEY environment variable not set.")
            raise ValueError("OPENAI_API_KEY environment variable not set.")
        if not self.model:
            logger.error("OPENAI_API_MODEL environment variable not set.")
            raise ValueError("OPENAI_API_MODEL environment variable not set.")
        self.client = openai.OpenAI(base_url=self.base_url, api_key=self.api_key, timeout=self.timeout)
        self._async_clients: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, openai.AsyncOpenAI] = weakref.WeakKeyDictionary()

    def _get_async_client(self) -> openai.AsyncOpenAI:
        """Returns an AsyncOpenAI client associated with the current event loop."""
        
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # Fallback for sync contexts or before loop starts
            # Note: We don't cache this as it's not tied to a loop
            http_client = httpx.AsyncClient(
                timeout=self.timeout,
                limits=httpx.Limits(max_keepalive_connections=0)
            )
            return openai.AsyncOpenAI(
                base_url=self.base_url, 
                api_key=self.api_key, 
                max_retries=3,
                http_client=http_client
            )

        if loop not in self._async_clients:
            logger.debug(f"Creating new AsyncOpenAI client for loop {id(loop)}")
            http_client = httpx.AsyncClient(
                timeout=self.timeout,
                limits=httpx.Limits(max_keepalive_connections=0)
            )
            self._async_clients[loop] = openai.AsyncOpenAI(
                base_url=self.base_url, 
                api_key=self.api_key, 
                max_retries=3,
                http_client=http_client
            )
        return self._async_clients[loop]

    def _convert_chat_history_to_messages(
        self, chat_history: list[Message]
    ) -> list[ChatCompletionMessageParam]:
        raw_messages: list[ChatCompletionMessageParam] = []
        send_thoughts = os.environ.get("LLM_SEND_THOUGHTS", "false").lower() == "true"

        for msg in chat_history:
            # Skip messages with role 'thought' - thoughts should be inline in assistant role
            if msg.role == MessageRole.THOUGHT:
                continue

            message_dict: dict[str, Any] = {"role": msg.role}

            # Handle Content (allow None if it's a pure tool call)
            content = msg.content or ""

            # Check if we should inject thoughts into content
            if send_thoughts and msg.role == MessageRole.ASSISTANT and msg.thought:
                # Format: [Thought] ... [/Thought] Narrative
                content = f"[Thought]\n{msg.thought}\n[/Thought]\n\n{content}".strip()

            if content:
                message_dict["content"] = content
            elif msg.content is None and not msg.tool_calls:
                 # Standardize empty content to None if no tool calls
                 message_dict["content"] = None

            # Handle Assistant Tool Calls
            if msg.role == MessageRole.ASSISTANT and msg.tool_calls:
                # Explicitly type the list of tool calls
                openai_tool_calls: list[ChatCompletionMessageToolCallParam] = []

                for tc in msg.tool_calls:
                    # Mypy will verify this dictionary matches the ToolCall definition
                    openai_tool_calls.append({
                        "id": tc.get("id", "call_unknown"),
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["arguments"]) if isinstance(tc["arguments"], dict) else tc["arguments"]
                        }
                    })

                # Cast or annotate the message_dict to the specific Assistant param type
                assistant_msg: ChatCompletionAssistantMessageParam = {
                    "role": "assistant",
                    "content": content or None,
                    "tool_calls": openai_tool_calls
                }
                raw_messages.append(assistant_msg)
                continue

            # Handle Tool Results
            if msg.role == MessageRole.TOOL:
                # Mypy usually doesn't allow 'name' in ChatCompletionToolMessageParam,
                # but some providers (and older OpenAI specs) support it for labeling.
                tool_msg: OpenAIToolMessageParam = {
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id or "unknown",
                    "content": msg.content or "",
                }
                # Some providers like 'name' in tool messages
                if msg.name:
                    tool_msg["name"] = msg.name

                raw_messages.append(tool_msg)
                continue

            # Fallback for regular messages (User, System, or simple Assistant)
            raw_messages.append(cast("ChatCompletionMessageParam", message_dict))

        return self._merge_consecutive_messages(raw_messages)

    def _merge_consecutive_messages(
        self, messages: list[ChatCompletionMessageParam]
    ) -> list[ChatCompletionMessageParam]:
        """
        Merges consecutive messages with the same role (user, assistant, system).
        Skips merging for 'tool' role as OpenAI requires them to stay separate.
        """
        if not messages:
            return []

        merged: list[dict[str, Any]] = []

        for msg in messages:
            msg_dict = cast(dict[str, Any], msg)
            role = msg_dict.get("role")

            if not merged:
                merged.append(msg_dict.copy())
                continue

            prev = merged[-1]
            # Roles to merge: system, user, assistant. Skip tool.
            if role == prev.get("role") and role in [MessageRole.USER, MessageRole.ASSISTANT, MessageRole.SYSTEM]:
                # 1. Merge Content
                content = msg_dict.get("content")
                prev_content = prev.get("content")

                if content:
                    if prev_content:
                        prev["content"] = f"{prev_content}\n\n{content}"
                    else:
                        prev["content"] = content

                # 2. Merge Tool Calls (for assistant)
                if role == MessageRole.ASSISTANT:
                    tool_calls = msg_dict.get("tool_calls")
                    if tool_calls:
                        if "tool_calls" not in prev:
                            prev["tool_calls"] = []
                        prev["tool_calls"].extend(tool_calls)

                        # Ensure content is None if it was empty (OpenAI requirement)
                        if not prev.get("content"):
                            prev["content"] = None
            else:
                merged.append(msg_dict.copy())

        return cast(list["ChatCompletionMessageParam"], merged)

    def _extract_reasoning(self, data: Any) -> str | None:
        """
        Helper to extract reasoning/thought from a message or delta object.
        Supports multiple common field names used by different providers.
        """
        if data is None:
            return None

        # 1. Attribute access (for pydantic/typed objects)
        # DeepSeek/OpenAI: reasoning_content, OpenRouter: reasoning, Claude: thinking
        for key in ["reasoning_content", "reasoning", "thinking"]:
            val = getattr(data, key, None)
        if val:
                return str(val)

        # 2. Dictionary fallback (for raw API data or dynamic types)
        if isinstance(data, dict):
            return data.get("reasoning_content") or data.get("reasoning") or data.get("thinking")

        # 3. Special handled cases for some providers that nest thinking (e.g. Mistral)
        # data.choices[0].delta.content[0].thinking[0].text
        # handled manually if needed, but the primary keys cover most.

        return None

    async def async_get_streaming_response(
        self, system_prompt: str, chat_history: list[Message]
    ) -> AsyncGenerator[str, None]:
        messages: list[ChatCompletionMessageParam] = [
            cast("ChatCompletionSystemMessageParam", {"role": MessageRole.SYSTEM, "content": system_prompt})
        ]
        converted_history = self._convert_chat_history_to_messages(chat_history)
        if not converted_history:
            converted_history.append(
                cast("ChatCompletionUserMessageParam", {"role": MessageRole.USER, "content": "Please proceed."})
            )
        messages.extend(converted_history)

        extra_params={
                # "chat_template_kwargs": {"enable_thinking": False},
                # "thinking": { "type": "disabled", "budget_tokens": 0 },
                "top_k": 50,
                "include_thoughts": True,
                "stop": ["<|im_end|>", "<|im_end|"]
            }

        async with self.semaphore:
            client = self._get_async_client()
            stream = await cast(Any, client.chat.completions).create(
                model=self.model or "gpt-4o",
                messages=messages,
                stream=True,
                stop=["<|im_end|>"],
                extra_body=extra_params,
            )
            has_started_reasoning = False
            has_started_content = False
            async for chunk in stream:
                typed_chunk = cast("ChatCompletionChunk", chunk)
                if typed_chunk.choices and len(typed_chunk.choices) > 0:
                    delta = typed_chunk.choices[0].delta

                    # 1. Capture and yield reasoning
                    reasoning = self._extract_reasoning(delta)
                    if reasoning:
                        if not has_started_reasoning:
                            yield "💭 "
                            has_started_reasoning = True
                        yield reasoning

                    # 2. Capture and yield content
                    if delta.content:
                        if not has_started_content:
                            if has_started_reasoning:
                                # Add a separator if reasoning preceded content
                                yield "\n\n---\n\n"
                            has_started_content = True
                        yield delta.content

    async def async_get_structured_response(
        self,
        system_prompt: str,
        chat_history: list[Message],
        output_schema: type[BaseModel],
        temperature: float = 0.5,
        top_p: float = 0.9,
    ) -> BaseModel:
        messages: list[ChatCompletionMessageParam] = [
            cast("ChatCompletionSystemMessageParam", {"role": MessageRole.SYSTEM, "content": system_prompt})
        ]
        converted_history = self._convert_chat_history_to_messages(chat_history)
        if not converted_history:
            converted_history.append(
                cast("ChatCompletionUserMessageParam", {"role": MessageRole.USER, "content": "Please proceed."})
            )
        messages.extend(converted_history)

        # Generate and clean the schema to satisfy strict backends
        json_schema = output_schema.model_json_schema()
        self._clean_schema(json_schema)

        extra_params={
                "top_k": 50,
                "include_thoughts": True,
                "stop": ["<|im_end|>", "<|im_end|"]
            }

        async with self.semaphore:
            client = self._get_async_client()
            resp = await asyncio.wait_for(
                cast(Any, client.chat.completions).create(
                    model=self.model or "gpt-4o",
                    messages=messages,
                    # max_completion_tokens omitted as requested for compatibility
                    temperature=temperature,
                    top_p=top_p,
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": output_schema.__name__,
                            "schema": json_schema,
                        },
                    },
                    stop=["<|im_end|>"],
                    extra_body=extra_params,
                    timeout=self.timeout
                ),
                timeout=self.timeout
            )

        if resp is None:
            raise ValueError("OpenAI returned None response.")

        typed_resp = cast("ChatCompletion", resp)
        if not typed_resp.choices or len(typed_resp.choices) == 0:
            raise ValueError("OpenAI returned no choices.")

        message = typed_resp.choices[0].message
        content = message.content
        if content is None:
            raise ValueError("OpenAI returned empty content.")

        # Capture reasoning even in structured response if available
        # Note: most providers don't support reasoning+json_schema yet, but some do.
        # We don't have a place to return 'thought' here as we return the validated model,
        # but we can log it or let the caller handle it if LLMResponse was returned.
        # For now, capturing content for validation.


        try:
            # Parse and validate
            validated = output_schema.model_validate_json(content)
            return validated

        except ValidationError as e:
            logger.error(f"Validation error in OpenAI response: {e}", exc_info=True)
            logger.error(f"Raw content: {content}")
            raise

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in OpenAI response: {e}", exc_info=True)
            logger.error(f"Raw content: {content}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred in get_structured_response: {e}", exc_info=True)
            logger.error(f"Raw content: {content}")
            raise

    def _clean_schema(self, schema: dict[str, Any]):
        """
        Recursively remove 'title' and 'default' fields from JSON schema,
        and flatten $ref fields by inlining their definitions from $defs.
        """
        # 1. Resolve and Inline references first (dereference)
        if "$defs" in schema:
            defs = schema.pop("$defs")
            self._resolve_references(schema, defs)

        # 2. Recursively clean remaining metadata
        self._recursive_clean(schema)

    def _resolve_references(self, schema: Any, defs: dict[str, Any]):
        """
        Recursively replaces "$ref" with the actual definition from defs.
        """
        if isinstance(schema, dict):
            if "$ref" in schema:
                ref_path = schema["$ref"]
                # Assumes local refs like "#/$defs/LocationData"
                ref_key = ref_path.split("/")[-1]
                if ref_key in defs:
                    # Replace the entire dict content with the definition
                    # We use update() to keep the same object reference if possible
                    definition = defs[ref_key].copy()
                    schema.clear()
                    schema.update(definition)
                    # Recursively resolve inside the newly inlined definition
                    self._resolve_references(schema, defs)
            else:
                for value in schema.values():
                    self._resolve_references(value, defs)
        elif isinstance(schema, list):
            for item in schema:
                self._resolve_references(item, defs)

    def _recursive_clean(self, schema: Any):
        """
        Recursively removes 'title' and 'default' from the schema.
        """
        if isinstance(schema, dict):
            schema.pop("title", None)
            schema.pop("default", None)
            # Some backends also dislike 'additionalProperties' if it's true,
            # but llama.cpp likes it if it's false. Pydantic 2.x often omits it
            # unless Config.extra is set.
            for value in schema.values():
                self._recursive_clean(value)
        elif isinstance(schema, list):
            for item in schema:
                self._recursive_clean(item)

    async def async_chat_with_tools(
        self,
        system_prompt: str,
        chat_history: list[Message],
        tools: list[dict[str, Any]],
    ) -> LLMResponse:
        messages: list[ChatCompletionMessageParam] = [
            cast("ChatCompletionSystemMessageParam", {"role": MessageRole.SYSTEM, "content": system_prompt})
        ]
        converted_history = self._convert_chat_history_to_messages(chat_history)
        if not converted_history:
            converted_history.append(
                cast("ChatCompletionUserMessageParam", {"role": MessageRole.USER, "content": "Please proceed."})
            )
        messages.extend(converted_history)

        extra_params={
                # "chat_template_kwargs": {"enable_thinking": False},
                # "thinking": { "type": "disabled", "budget_tokens": 0 },
                "top_k": 50,
                "include_thoughts": True,
                "stop": ["<|im_end|>", "<|im_end|"]
            }

        async with self.semaphore:
            client = self._get_async_client()
            response = await asyncio.wait_for(
                cast(Any, client.chat.completions).create(
                    model=self.model or "gpt-4o",
                    messages=messages,
                    tools=tools,
                    tool_choice="auto" if tools else None,
                    temperature=0.5,
                    extra_body=extra_params,
                ),
                timeout=self.timeout
            )

        if response is None:
             return LLMResponse(content=None, tool_calls=None)

        typed_resp = cast("ChatCompletion", response)
        if not typed_resp.choices or len(typed_resp.choices) == 0:
            return LLMResponse(content=None, tool_calls=None)

        message = typed_resp.choices[0].message
        thought_text = self._extract_reasoning(message)

        tool_calls_data = []

        if message.tool_calls:
            for tool_call in message.tool_calls:
                try:
                    tool_calls_data.append({
                        "name": tool_call.function.name,
                        "arguments": json.loads(tool_call.function.arguments),
                        "id": tool_call.id
                    })
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode arguments for {tool_call.function.name}")

        return LLMResponse(
            content=message.content,
            thought=thought_text if thought_text else None,
            tool_calls=tool_calls_data if tool_calls_data else None
        )
