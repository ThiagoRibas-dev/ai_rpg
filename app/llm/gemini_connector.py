import os
import json
import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration
from typing import Generator, List, Dict, Any, Type
from pydantic import BaseModel
from app.llm.llm_connector import LLMConnector

class GeminiConnector(LLMConnector):
    """
    A class to handle communication with the Google Gemini API.
    """

    def __init__(self):
        """
        Initializes the GeminiConnector, configuring the Gemini client.
        """
        api_key = os.environ.get("GEMINI_API_KEY")
        model_name = os.environ.get("GEMINI_API_MODEL")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")
        if not model_name:
            raise ValueError("GEMINI_API_MODEL environment variable not set.")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    def get_streaming_response(self, prompt: str) -> Generator[str, None, None]:
        """
        Yields a stream of string responses from the Gemini API.
        """
        response = self.model.generate_content(prompt, stream=True)
        for chunk in response:
            if chunk.text:
                yield chunk.text

    def get_structured_response(self, prompt: str, tools: List[Dict[str, Any]], output_schema: Type[BaseModel]) -> Dict[str, Any]:
        """
        Returns a structured JSON response from the Gemini API that conforms to the
        provided Pydantic schema.
        """
        # Convert tool schemas to Gemini's FunctionDeclaration format
        gemini_tools = [FunctionDeclaration(**tool) for tool in tools] if tools else None

        response = self.model.generate_content(
            prompt,
            tools=gemini_tools,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
                response_schema=output_schema,
            ),
        )
        # The API returns a structured object that pydantic can parse directly
        return response.candidates.content.parts.function_call if response.candidates.content.parts.function_call else json.loads(response.text)