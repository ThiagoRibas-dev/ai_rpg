import os
import json
import openai
from typing import Dict, Any, Type
from pydantic import BaseModel
from app.llm.llm_connector import LLMConnector

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

    def get_streaming_response(self, prompt: str):
        messages = [{"role": "user", "content": prompt}]
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
        )
        for chunk in stream:
            # Correct access pattern
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def get_structured_response(self, prompt: str, output_schema: Type[BaseModel]) -> Dict[str, Any]:
        # Force JSON-only response matching the schema
        messages = [
            {
                "role": "system",
                "content": f"Return strictly valid JSON matching this schema. No extra keys, no comments:\n{output_schema.model_json_schema()}",
            },
            {"role": "user", "content": prompt},
        ]
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content
        return json.loads(content)