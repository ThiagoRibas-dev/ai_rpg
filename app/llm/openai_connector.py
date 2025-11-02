import os
import json
import openai
from typing import Dict, Type, List, Generator
from pydantic import BaseModel
from app.llm.llm_connector import LLMConnector
from app.models.message import Message

class OpenAIConnector(LLMConnector):
    def __init__(self):
        self.base_url = os.environ.get("OPENAI_API_BASE_URL")
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.model = os.environ.get("OPENAI_API_MODEL")
        if not self.base_url:
            raise ValueError("OPENAI_API_BASE_URL environment variable not set.")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set.")
        if not self.model:
            raise ValueError("OPENAI_API_MODEL environment variable not set.")
        self.client = openai.OpenAI(base_url=self.base_url, api_key=self.api_key)

    def _convert_chat_history_to_messages(self, chat_history: List[Message]) -> List[Dict[str, str]]:
        messages = []
        for msg in chat_history:
            messages.append({"role": msg.role, "content": msg.content})
        return messages

    def get_streaming_response(self, system_prompt: str, chat_history: List[Message]) -> Generator[str, None, None]:
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self._convert_chat_history_to_messages(chat_history))
        
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def get_structured_response(self, system_prompt: str, chat_history: List[Message], output_schema: Type[BaseModel]) -> BaseModel:
        messages = [
            {
                "role": "system",
                "content": f"{system_prompt}\nReturn strictly valid JSON matching this schema. No extra keys, no comments:\n{output_schema.model_json_schema()}",
            }
        ]
        messages.extend(self._convert_chat_history_to_messages(chat_history))

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content
        return json.loads(content)
