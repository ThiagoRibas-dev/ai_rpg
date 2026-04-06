from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
from collections.abc import AsyncGenerator
from typing import Any, cast

from google import genai
from google.genai import types
from google.genai.types import HttpOptions
from pydantic import BaseModel

from app.llm.llm_connector import LLMConnector, LLMResponse
from app.models.message import Message
from app.models.vocabulary import MessageRole

logger = logging.getLogger(__name__)


class GeminiConnector(LLMConnector):
    def __init__(self):
        super().__init__()
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")

        self.model_name = os.environ.get("GEMINI_API_MODEL")
        if not self.model_name:
            self.model_name = "gemini-flash-latest" # Updated default

        self.client = genai.Client(
            api_key=api_key,
            http_options=HttpOptions(timeout=self.timeout)
        )
        self.default_max_tokens = 65535
        self.default_thinking_budget = 12000
        self.default_safety_settings = [
            types.SafetySetting(
                category="HARM_CATEGORY_HARASSMENT",
                threshold="BLOCK_NONE",
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_HATE_SPEECH",
                threshold="BLOCK_NONE",
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                threshold="BLOCK_NONE",
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT",
                threshold="BLOCK_NONE",
            ),
        ]

    def _convert_chat_history_to_contents(
        self, chat_history: list[Message]
    ) -> list[types.Content]:
        contents = []

        for msg in chat_history:
            if msg.role == MessageRole.SYSTEM:
                continue

            # --- 1. Handle User Messages ---
            if msg.role == MessageRole.USER:
                content_text = msg.content or ""
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=content_text)]
                ))

            # --- 2. Handle Assistant (Model) Messages ---
            elif msg.role == MessageRole.ASSISTANT:
                parts = []

                # B. Text Content
                if msg.content:
                    parts.append(types.Part.from_text(text=msg.content))

                # C. Thought Content
                if getattr(msg, 'thought', None):
                    parts.append(types.Part(
                        thought=True,
                        text=msg.thought,
                    ))

                    # Decode the stored base64 thought_signature back to bytes.
                    sig_bytes: bytes | None = None
                    if getattr(msg, 'thought_signature', None):
                        try:
                            # Cast to str because we know the signature is stored as base64 string
                            sig_str = cast(str, msg.thought_signature)
                            sig_bytes = base64.b64decode(sig_str)
                        except Exception:
                            sig_bytes = None

                    # Gemini API requires the signature ONLY on the first function call
                    t_calls = msg.tool_calls or []
                    for idx, tool_call in enumerate(t_calls):
                        fc = types.FunctionCall(
                            name=tool_call["name"],
                            args=tool_call["arguments"]
                        )
                        if idx == 0 and sig_bytes:
                            # Use constructor directly to avoid ambiguous dict unpacking
                            parts.append(types.Part(function_call=fc, thought_signature=sig_bytes))
                        else:
                            parts.append(types.Part(function_call=fc))

                if parts:
                    contents.append(types.Content(role="model", parts=parts))

            # --- 3. Handle Tool Results ---
            elif msg.role == MessageRole.TOOL:
                try:
                    tool_content = msg.content or "{}"
                    response_data = json.loads(tool_content)
                except Exception:
                    response_data = {"result": msg.content}

                if not isinstance(response_data, dict):
                    response_data = {"result": response_data}

                part = types.Part.from_function_response(
                    name=msg.name or "unknown_tool",
                    response=response_data
                )

                if contents and contents[-1].role == "user":
                    target_parts = contents[-1].parts
                    if target_parts is not None:
                        target_parts.append(part)
                    else:
                        contents[-1].parts = [part]
                else:
                    contents.append(types.Content(role="user", parts=[part]))

        return contents

    async def async_get_streaming_response(
        self, system_prompt: str, chat_history: list[Message]
    ) -> AsyncGenerator[str, None]:
        contents = self._convert_chat_history_to_contents(chat_history)
        if not contents:
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text="Please proceed.")]))

        config = {
            "system_instruction": [types.Part.from_text(text=system_prompt)],
            "temperature": 1,
            "top_p": 0.9,
            "top_k": 50,
            "max_output_tokens": self.default_max_tokens,
            "safety_settings": self.default_safety_settings,
        }
        # If model supports thinking, we add the config
        model_nm = self.model_name or ""
        if "flash" in model_nm.lower() or "thought" in model_nm.lower():
             config["thinking_config"] = types.ThinkingConfig(
                thinking_budget=self.default_thinking_budget
            )

        generation_config = types.GenerateContentConfig(**config)

        async with self.semaphore:
            # Cast to Any to bypass complex tool-call overloads that block Mypy
            response = await cast(Any, self.client.aio.models).generate_content_stream(
                model=self.model_name or "gemini-2.0-flash",
                contents=cast(Any, contents),
                config=generation_config,
            )
            async for chunk in response:
                chunk_text = getattr(chunk, "text", None)
                if chunk_text:
                    yield str(chunk_text)

    async def async_get_structured_response(
        self,
        system_prompt: str,
        chat_history: list[Message],
        output_schema: type[BaseModel],
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> BaseModel:
        contents = self._convert_chat_history_to_contents(chat_history)
        if not contents:
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text="Please proceed.")]))

        generation_config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=output_schema.model_json_schema(),
            system_instruction=[types.Part.from_text(text=system_prompt)],
            temperature=temperature,
            top_p=top_p,
            max_output_tokens=self.default_max_tokens,
            safety_settings=self.default_safety_settings,
        )

        model_lower = (self.model_name or "").lower()
        if "flash" in model_lower or "thought" in model_lower:
             generation_config.thinking_config = types.ThinkingConfig(
                thinking_budget=self.default_thinking_budget
            )

        async with self.semaphore:
            response = await asyncio.wait_for(
                self.client.aio.models.generate_content(
                    model=self.model_name or "gemini-flash-latest",
                    contents=cast(Any, contents),
                    config=generation_config
                ),
                timeout=self.timeout
            )

        if response.parsed:
            return output_schema.model_validate(response.parsed)

        if response.text:
            try:
                data = json.loads(response.text)
                return output_schema.model_validate(data)
            except Exception as e:
                logger.error(f"Gemini structured response failure. Raw text: {response.text}")
                raise ValueError(f"Failed to parse Gemini response: {e}") from e

        raise ValueError("Gemini returned empty response (blocked or error).")

    async def async_chat_with_tools(
        self,
        system_prompt: str,
        chat_history: list[Message],
        tools: list[dict[str, Any]],
    ) -> LLMResponse:
        contents = self._convert_chat_history_to_contents(chat_history)
        if not contents:
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text="Please proceed.")]))

        function_declarations = [
            types.FunctionDeclaration(**t["function"]) for t in tools
        ]
        gemini_tool = types.Tool(function_declarations=function_declarations)

        config_args = {
            "system_instruction": [types.Part.from_text(text=system_prompt)],
            "tools": [gemini_tool],
            "temperature": 0.5,
            "max_output_tokens": self.default_max_tokens,
            "safety_settings": self.default_safety_settings,
        }

        # Check for model thinking capabilities
        model_lower = (self.model_name or "").lower()
        if "flash" in model_lower or "thought" in model_lower:
             config_args["thinking_config"] = types.ThinkingConfig(
                thinking_budget=self.default_thinking_budget
            )

        generation_config = types.GenerateContentConfig(**config_args)

        async with self.semaphore:
            response = await asyncio.wait_for(
                self.client.aio.models.generate_content(
                    model=self.model_name or "gemini-flash-latest",
                    contents=cast(Any, contents),
                    config=generation_config
                ),
                timeout=self.timeout
            )

        content_text = ""
        thought_text = ""
        thought_sig = None
        tool_calls = []

        if (
            response.candidates
            and len(response.candidates) > 0
            and response.candidates[0].content
            and response.candidates[0].content.parts
        ):
            for part in response.candidates[0].content.parts:
                if part is None:
                    continue

                if getattr(part, "thought", None) and getattr(part, "text", None):
                    thought_text += str(part.text)
                elif getattr(part, "text", None):
                    content_text += str(part.text)

                # Capture thought_signature (bytes) from any part that has it
                t_sig = getattr(part, "thought_signature", None)
                if t_sig and thought_sig is None:
                    thought_sig = base64.b64encode(cast(bytes, t_sig)).decode(
                        "ascii"
                    )

                if part.function_call:
                    tool_calls.append(
                        {
                            "name": part.function_call.name,
                            "arguments": dict(part.function_call.args)
                            if part.function_call.args
                            else {},
                            "id": "call_gemini_" + str(part.function_call.name),
                        }
                    )


        return LLMResponse(
            content=content_text,
            thought=thought_text if thought_text else None,
            thought_signature=thought_sig,
            tool_calls=tool_calls if tool_calls else None
        )

