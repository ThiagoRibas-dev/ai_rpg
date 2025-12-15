import os
import json
import logging
from google import genai
from google.genai import types
from pydantic import BaseModel

from typing import Type, List, Generator, Dict, Any
from app.llm.llm_connector import LLMConnector, LLMResponse
from app.models.message import Message

logger = logging.getLogger(__name__)


class GeminiConnector(LLMConnector):
    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")

        self.model_name = os.environ.get("GEMINI_API_MODEL")
        if not self.model_name:
            self.model_name = "gemini-flash-latest" # Updated default
        
        self.client = genai.Client(api_key=api_key)
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
        self, chat_history: List[Message]
    ) -> List[types.Content]:
        contents = []
        
        for msg in chat_history:
            if msg.role == "system":
                continue  # System prompt is handled separately in config

            # --- 1. Handle User Messages ---
            if msg.role == "user":
                contents.append(types.Content(
                    role="user", 
                    parts=[types.Part.from_text(text=msg.content)]
                ))

            # --- 2. Handle Assistant (Model) Messages ---
            elif msg.role == "assistant":
                parts = []
                
                # A. Text Content (Thought)
                if msg.content:
                    parts.append(types.Part.from_text(text=msg.content))
                
                # B. Tool Calls
                if msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        fn_name = tool_call["name"]
                        fn_args = tool_call["arguments"] # Should be a dict
                        
                        parts.append(types.Part.from_function_call(
                            name=fn_name, 
                            args=fn_args
                        ))
                
                if parts:
                    contents.append(types.Content(role="model", parts=parts))

            # --- 3. Handle Tool Results ---
            elif msg.role == "tool":
                # OpenAI Protocol: role="tool", content="JSON_STRING", name="tool_name"
                # Gemini Protocol: role="user", parts=[Part(function_response=...)]
                
                try:
                    # Gemini expects a Dict, not a JSON string.
                    response_data = json.loads(msg.content)
                except Exception:
                    # Fallback for simple strings
                    response_data = {"result": msg.content}

                # Create the FunctionResponse part
                # Important: 'name' must match the function that was called.
                part = types.Part.from_function_response(
                    name=msg.name, 
                    response=response_data
                )
                
                # Gemini Merge Logic: 
                # If the LAST message was also a 'tool' result (User role), append to it.
                # This handles parallel tool execution where multiple results return in one turn.
                if contents and contents[-1].role == "user":
                    # Check if the last message is purely tool responses or mixed.
                    # Usually safest to append if the previous was a tool response too.
                    # For simplicity, we append to the user turn.
                    contents[-1].parts.append(part)
                else:
                    contents.append(types.Content(role="user", parts=[part]))

        return contents

    def get_streaming_response(
        self, system_prompt: str, chat_history: List[Message]
    ) -> Generator[str, None, None]:
        contents = self._convert_chat_history_to_contents(chat_history)
 
        if not contents:
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text="Please proceed.")]))

        config = {
            "system_instruction": [types.Part.from_text(text=system_prompt)],
            "temperature": 1,
            "top_p": 0.9,
            "top_k": 50,
            "max_output_tokens": self.default_max_tokens,
            "thinking_config": types.ThinkingConfig(
                thinking_budget=self.default_thinking_budget
            ),
            "safety_settings": self.default_safety_settings,
        }
        generation_config = types.GenerateContentConfig(**config)

        response = self.client.models.generate_content_stream(
            model=self.model_name,
            contents=contents,
            config=generation_config,
        )
        for chunk in response:
            if getattr(chunk, "text", None):
                yield chunk.text

    def get_structured_response(
        self,
        system_prompt: str,
        chat_history: List[Message],
        output_schema: Type[BaseModel],
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
            thinking_config=types.ThinkingConfig(
                thinking_budget=self.default_thinking_budget
            ),
            safety_settings=self.default_safety_settings,
        )

        response = self.client.models.generate_content(
            model=self.model_name, contents=contents, config=generation_config
        )
        
        if response.parsed:
            return output_schema.model_validate(response.parsed)
            
        if response.text:
            try:
                data = json.loads(response.text)
                return output_schema.model_validate(data)
            except Exception as e:
                logger.error(f"Gemini structured response failure. Raw text: {response.text}")
                raise ValueError(f"Failed to parse Gemini response: {e}")
        
        raise ValueError("Gemini returned empty response (blocked or error).")

    def get_tool_calls(self, system_prompt, chat_history, tools):
        return [] # Legacy stub

    def chat_with_tools(
        self,
        system_prompt: str,
        chat_history: List[Message],
        tools: List[Dict[str, Any]],
    ) -> LLMResponse:
        contents = self._convert_chat_history_to_contents(chat_history)
        if not contents:
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text="Please proceed.")]))

        # Convert schema format
        function_declarations = [
            types.FunctionDeclaration(**t["function"]) for t in tools
        ]
        gemini_tool = types.Tool(function_declarations=function_declarations)

        generation_config = types.GenerateContentConfig(
            system_instruction=[types.Part.from_text(text=system_prompt)],
            tools=[gemini_tool],
            temperature=0.7,
            max_output_tokens=self.default_max_tokens,
            safety_settings=self.default_safety_settings,
        )

        response = self.client.models.generate_content(
            model=self.model_name, contents=contents, config=generation_config
        )

        content_text = ""
        tool_calls = []

        # Gemini returns candidates -> content -> parts
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.text:
                    content_text += part.text
                if part.function_call:
                    # Standardize to our internal format
                    tool_calls.append({
                        "name": part.function_call.name,
                        "arguments": dict(part.function_call.args),
                        "id": "call_gemini_" + part.function_call.name # Gemini doesn't use IDs, make one up for internal tracking
                    })

        return LLMResponse(content=content_text, tool_calls=tool_calls if tool_calls else None)
