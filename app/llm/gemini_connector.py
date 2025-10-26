import os
from google import genai
from google.genai import types
from pydantic import BaseModel

from typing import Dict, Any, Type, List, Generator
from app.llm.llm_connector import LLMConnector
from app.models.message import Message

class GeminiConnector(LLMConnector):
    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")

        self.model_name = os.environ.get("GEMINI_API_MODEL")
        if not self.model_name:
            self.model_name = "gemini-2.5-flash"
        if not self.model_name:
            raise ValueError("GEMINI_API_MODEL environment variable not set.")

        self.client = genai.Client(api_key=api_key)
        self.default_max_tokens = 65535
        self.default_thinking_budget = 12000
        self.default_safety_settings = [
            types.SafetySetting(
                category="HARM_CATEGORY_HARASSMENT",
                threshold="BLOCK_NONE",  # Block none
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_HATE_SPEECH",
                threshold="BLOCK_NONE",  # Block none
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                threshold="BLOCK_NONE",  # Block none
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT",
                threshold="BLOCK_NONE",  # Block none
            )
        ]

    def _convert_chat_history_to_contents(self, chat_history: List[Message]) -> List[types.Content]:
        contents = []
        for msg in chat_history:
            role = "model" if msg.role == "assistant" or msg.role == "system" else msg.role
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=msg.content)]))
        return contents

    def get_streaming_response(self, system_prompt: str, chat_history: List[Message]) -> Generator[str, None, None]:
        contents = self._convert_chat_history_to_contents(chat_history)
        
        config = {
            "system_instruction": [types.Part.from_text(text=system_prompt)],
            "temperature": 1,
            "top_p": 0.9,
            "top_k": 50,
            "max_output_tokens": self.default_max_tokens,
            "thinking_config": types.ThinkingConfig(
                thinking_budget=self.default_thinking_budget
            ),
            "safety_settings": self.default_safety_settings
        }
        generation_config = types.GenerateContentConfig(**config)

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=generation_config,
            stream=True
        )
        for chunk in response:
            if getattr(chunk, "text", None):
                yield chunk.text

    def get_structured_response(
        self, system_prompt: str, chat_history: List[Message], output_schema: Type[BaseModel]
    ) -> Dict[str, Any]:
        # We intentionally do NOT pass tools here, because Gemini FunctionDeclarations
        # are picky and don't allow $ref/anyOf/etc. We stick to Structured Output.
        contents = self._convert_chat_history_to_contents(chat_history)

        config = {
            "response_mime_type": "application/json",
            "response_schema": output_schema,
            "system_instruction": [types.Part.from_text(text=system_prompt)],
            "temperature": 1,
            "top_p": 0.9,
            "max_output_tokens": self.default_max_tokens,
            "thinking_config": types.ThinkingConfig(
                thinking_budget=self.default_thinking_budget
            ),
            "safety_settings": self.default_safety_settings
        }
        generation_config = types.GenerateContentConfig(**config)

        response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=generation_config
                )
        return response.parsed
