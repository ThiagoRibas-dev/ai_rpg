import os
import google.generativeai as genai
from typing import Generator
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