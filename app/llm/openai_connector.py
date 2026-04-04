from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any, cast

import openai
from pydantic import BaseModel, ValidationError

from app.llm.llm_connector import LLMConnector, LLMResponse
from app.models.message import Message
from app.models.vocabulary import MessageRole

if TYPE_CHECKING:
    from openai.types.chat import (
        ChatCompletion,
        ChatCompletionChunk,
        ChatCompletionMessageParam,
        ChatCompletionSystemMessageParam,
        ChatCompletionUserMessageParam,
    )


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
        self.client = openai.OpenAI(base_url=self.base_url, api_key=self.api_key)
        self.async_client = openai.AsyncOpenAI(base_url=self.base_url, api_key=self.api_key)

    def _convert_chat_history_to_messages(
        self, chat_history: list[Message]
    ) -> list[ChatCompletionMessageParam]:
        messages: list[ChatCompletionMessageParam] = []
        for msg in chat_history:
            message_dict: dict[str, Any] = {"role": msg.role}

            # Handle Content (allow None if it's a pure tool call)
            if msg.content is not None:
                message_dict["content"] = msg.content

            # Handle Assistant Tool Calls
            if msg.role == MessageRole.ASSISTANT and msg.tool_calls:
                # Convert our internal normalized format back to OpenAI API format
                openai_tool_calls = []
                for tc in msg.tool_calls:
                    openai_tool_calls.append({
                        "id": tc.get("id", "call_unknown"),
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["arguments"]) if isinstance(tc["arguments"], dict) else tc["arguments"]
                        }
                    })
                message_dict["tool_calls"] = openai_tool_calls

                # OpenAI sometimes requires content to be null if missing
                if "content" not in message_dict:
                    message_dict["content"] = None

            # Handle Tool Results
            if msg.role == MessageRole.TOOL:
                if not msg.tool_call_id:
                    # Fallback for legacy messages or errors
                    logger.warning("Message with role 'tool' missing 'tool_call_id'.")
                    message_dict["tool_call_id"] = "unknown_call_id"
                else:
                    message_dict["tool_call_id"] = msg.tool_call_id

                # Some local servers (and OpenAI) allow/expect 'name'
                if msg.name:
                    message_dict["name"] = msg.name

            messages.append(cast("ChatCompletionMessageParam", message_dict))
        return messages

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
                "stop": ["<|im_end|>", "<|im_end|"]
            }

        async with self.semaphore:
            stream = await cast(Any, self.async_client.chat.completions).create(
                model=self.model or "gpt-4o",
                messages=messages,
                stream=True,
                stop=["<|im_end|>"],
                extra_body=extra_params,
            )
            async for chunk in stream:
                typed_chunk = cast("ChatCompletionChunk", chunk)
                if (
                    typed_chunk.choices
                    and len(typed_chunk.choices) > 0
                    and typed_chunk.choices[0].delta
                    and typed_chunk.choices[0].delta.content
                ):
                    yield typed_chunk.choices[0].delta.content

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
                # "chat_template_kwargs": {"enable_thinking": False},
                # "thinking": { "type": "disabled", "budget_tokens": 0 },
                "top_k": 50,
                "json_schema": json_schema,
                "response_format": {
                    "type": "json_object",
                    "schema": json_schema,
                },
                "stop": ["<|im_end|>", "<|im_end|"]
            }

        async with self.semaphore:
            resp = await asyncio.wait_for(
                cast(Any, self.async_client.chat.completions).create(
                    model=self.model or "gpt-4o",
                    messages=messages,
                    max_completion_tokens=-1,
                    temperature=temperature,
                    top_p=top_p,
                    response_format={
                        "type": "json_schema",
                        "schema": json_schema,
                    },
                    stop=["<|im_end|>"],
                    extra_body=extra_params,
                ),
                timeout=self.timeout
            )

        if resp is None:
            raise ValueError("OpenAI returned None response.")

        typed_resp = cast("ChatCompletion", resp)
        if not typed_resp.choices or len(typed_resp.choices) == 0:
            raise ValueError("OpenAI returned no choices.")

        content = typed_resp.choices[0].message.content
        if content is None:
            raise ValueError("OpenAI returned empty content.")


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
                "stop": ["<|im_end|>", "<|im_end|"]
            }

        async with self.semaphore:
            response = await asyncio.wait_for(
                cast(Any, self.async_client.chat.completions).create(
                    model=self.model or "gpt-4o",
                    messages=messages,
                    tools=tools,
                    tool_choice="auto" if tools else None,
                    temperature=0.25,
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
            tool_calls=tool_calls_data if tool_calls_data else None
        )
