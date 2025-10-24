import os
import json
import openai
from typing import Generator, List, Dict, Any, Type
from pydantic import BaseModel
from app.llm.llm_connector import LLMConnector

class OpenAIConnector(LLMConnector):
    """
    A class to handle communication with OpenAI-compatible APIs.
    """

    def __init__(self):
        """
        Initializes the OpenAIConnector, configuring the API client.
        """
        self.base_url = os.environ.get("OPENAI_API_BASE_URL")
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.model = os.environ.get("OPENAI_API_MODEL")
        
        if not self.base_url:
            raise ValueError("OPENAI_API_BASE_URL environment variable not set.")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set.")
        if not self.model:
            raise ValueError("OPENAI_API_MODEL environment variable not set.")

        self.client = openai.OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
        )

    def get_streaming_response(self, prompt: str) -> Generator[str, None, None]:
        """
        Yields a stream of string responses from an OpenAI-compatible API.
        """
        messages = [{"role": "user", "content": prompt}]
        
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
        )
        
        for chunk in stream:
            if chunk.choices.delta.content:
                yield chunk.choices.delta.content

    def get_structured_response(self, prompt: str, tools: List[Dict[str, Any]], output_schema: Type[BaseModel]) -> Dict[str, Any]:
        """
        Returns a structured JSON response from an OpenAI-compatible API that
        conforms to the provided Pydantic schema.
        """
        messages = [{"role": "user", "content": prompt}]
        
        # Forcing JSON output with a system message is a common technique.
        messages.insert(0, {
            "role": "system",
            "content": f"Please respond with a JSON object that adheres to this schema: {output_schema.model_json_schema()}"
        })

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            response_format={"type": "json_object"},
        )
        
        return json.loads(response.choices.message.content)