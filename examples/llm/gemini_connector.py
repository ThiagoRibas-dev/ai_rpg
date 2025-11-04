import os
import json
import time
import logging
import traceback
from google import genai
from google.genai import types
from pydantic import ValidationError, create_model, Field
from typing import Optional

from app.llm.prompts import GameLoopPrompts
from app.schemas.wrapper_schemas import DualResponse
from app.schemas.action_request import ActionRequest


class GeminiConnector:
    """
    A class to handle communication with the Google Gemini API.
    Supports both structured JSON output and conversational streaming.
    """

    def __init__(self):
        """
        Initializes the GeminiConnector, configuring the Gemini client.
        """

        api_keys_str = os.environ.get("GEMINI_API_KEY")
        if not api_keys_str:
            raise ValueError("GEMINI_API_KEY environment variable not set.")
        
        self.api_keys = [key.strip() for key in api_keys_str.split(',') if key.strip()]
        if not self.api_keys:
            raise ValueError("No valid GEMINI_API_KEY found in environment variable.")
        
        self.current_key_index = 0
        self.client = self._initialize_client()
        
        self.last_call_time = 0
        self.min_time_between_calls = 5 # 1 second minimum between calls

        self.default_model_name = 'gemini-2.5-flash'
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

    def _initialize_client(self):
        """Initializes the genai client with the current API key."""
        api_key = self.api_keys[self.current_key_index]
        return genai.Client(api_key=api_key)

    def _get_next_api_key(self):
        """Rotates to the next API key in the list."""
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        return self.api_keys[self.current_key_index]

    def generate_structured_response(
        self,
        action_request: ActionRequest,
        max_retries: int = 3,
        retry_prompt: Optional[str] = None
    ) -> DualResponse:
        """
        Generates a dual response containing both a conversational chat reply and
        structured JSON data, with a robust retry mechanism for empty or invalid responses.
        """
        # Extract data from ActionRequest
        instruction = action_request.instruction
        chat_history = action_request.chat_history
        response_schema = action_request.response_schema
        context_data = action_request.context_data

        # 1. Dynamically create the wrapper schema
        DynamicDualResponse = create_model(
            'DynamicDualResponse',
            __base__=DualResponse,
            generated_data=(response_schema, Field(description="The structured data requested."))
        )

        # 2. Construct the system instruction
        system_parts = [
            "# D&D 3.5e Game.",
            "Dungeon Master personality : Default - Professional. Will addapt to the campaign's tone and themes.",
            instruction
            # "You must provide a conversational reply in the `chat_reply` field and the structured data in the `generated_data` field."
        ]
        if context_data:
            system_parts.append("\n--- Context Data ---")
            system_parts.append(context_data)
        system_instruction_text = "\n".join(system_parts)

        # 3. Construct the initial multi-turn contents
        base_contents = []
        for message in chat_history:
            role = "model" if message.role in ("system", "error") else message.role
            base_contents.append(types.Content(role=role, parts=[types.Part.from_text(text=message.content)]))

        json_schema = DynamicDualResponse.model_json_schema()
        
        # 4. Build the generation config
        config = {
            "response_mime_type": "application/json",
            # "response_json_schema": json_schema,
            "response_schema": DynamicDualResponse,
            "system_instruction": [types.Part.from_text(text=system_instruction_text)],
            "temperature": 1,
            "top_p": 0.9,
            "max_output_tokens": self.default_max_tokens,
            "thinking_config": types.ThinkingConfig(
                thinking_budget=self.default_thinking_budget
            ),
            "safety_settings": self.default_safety_settings
        }
        generation_config = types.GenerateContentConfig(**config)

        # 5. Call the API with retry logic
        for attempt in range(max_retries):
            # Create a temporary copy of contents for each attempt to avoid mutation
            current_contents = list(base_contents)
            
            try:
                if attempt > 0:
                    # Use the specific retry prompt if provided, otherwise use a generic one.
                    prompt_to_use = retry_prompt or GameLoopPrompts.RETRY_WITH_INSTRUCTIONS
                    current_contents.append(types.Content(
                        role="user", 
                        parts=[types.Part.from_text(text=prompt_to_use)]
                    ))

                print("---" + "-" * 10 + " DEBUG SEND " + "-" * 10 + "---")
                print("\n")
                print("Schema")
                print("\n")
                # print(json.dumps(json_schema, indent=2))
                path = os.path.join("debug_dump.json")
                try:
                    with open(path, 'w') as f:
                        json.dump(json_schema, f, indent=2)
                    logging.info(f"Saved debug json to {path}")
                except Exception as e:
                    logging.exception(f"Failed to save debug json to {path}: {e}")
                print("\n")
                # print(self.default_model_name)
                # print("\n")
                # print(current_contents)
                # print("\n")
                # print(generation_config)
                # print("\n")
                print("\n")

                # Enforce rate limit
                current_time = time.time()
                time_elapsed = current_time - self.last_call_time
                if time_elapsed < self.min_time_between_calls:
                    sleep_duration = self.min_time_between_calls - time_elapsed
                    logging.info(f"Rate limit hit. Sleeping for {sleep_duration:.2f} seconds.")
                    time.sleep(sleep_duration)
                self.last_call_time = time.time()

                # Rotate API key and reinitialize client
                self.client = self._initialize_client()

                response = self.client.models.generate_content(
                    model=self.default_model_name,
                    contents=current_contents, # Use the temporary copy
                    config=generation_config
                )
                response_json = response.parsed
                
                print("---" + "-" * 10 + " DEBUG RESPONSE " + "-" * 10 + "---")
                print("\n")
                print(response_json)
                print("\n")

                if response_json:
                    if isinstance(response_json, DynamicDualResponse):
                        return response_json
                    return DynamicDualResponse(**response_json)

                logging.warning(f"LLM returned empty response on attempt {attempt + 1}/{max_retries} for instruction: '{instruction[:80]}...'" )
                time.sleep(30)
                attempt += 1
            except (json.JSONDecodeError, TypeError, ValidationError) as e:
                logging.error(f"Error parsing/validating LLM JSON on attempt {attempt + 1}/{max_retries} for instruction: '{instruction[:80]}...'. Error: {e}")
                raw_response_content = getattr(response, 'text', 'N/A')
                if attempt == max_retries - 1:
                    logging.error(traceback.format_exc()) # Log the full stack trace
                    return DualResponse(chat_reply=f"An error occurred after multiple retries: {e}", generated_data={"error": f"Failed to parse or validate LLM JSON. Raw text: {raw_response_content}."})
                time.sleep(30)
            except Exception as e:
                logging.error(f"Unexpected error on attempt {attempt + 1}/{max_retries} for instruction: '{instruction[:80]}...'. Error: {e}")
                if attempt == max_retries - 1:
                    logging.error(traceback.format_exc()) # Log the full stack trace
                    # logging.debug(generation_config)
                    return DualResponse(chat_reply=f"An unexpected error occurred after multiple retries: {e}", generated_data={"error": str(e)})
                time.sleep(30)

        # If all retries fail
        error_message = f"LLM returned no content after {max_retries} retries for instruction: '{instruction[:80]}...'"
        logging.error(error_message)
        return DualResponse(chat_reply=error_message, generated_data={"error": error_message})

    def generate_chat_response(self, action_request: ActionRequest) -> str:
        """
        Generates a conversational response from the Gemini API.
        """
        # Extract data from ActionRequest
        instruction = action_request.instruction
        chat_history = action_request.chat_history
        context_data = action_request.context_data

        # Construct the system instruction
        system_parts = [
            "# D&D 3.5e Game.",
            "Dungeon Master personality : Default - Professional. Will addapt to the campaign's tone and themes.",
            instruction
            # "You must provide a conversational reply."
        ]
        if context_data:
            system_parts.append("\n--- Context Data ---")
            system_parts.append(context_data)
        system_instruction_text = "\n".join(system_parts)

        # Construct the multi-turn contents
        contents = []
        for message in chat_history:
            role = "model" if message.role in ("system", "error") else message.role
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=message.content)]))

        # Build the generation config
        config = {
            "system_instruction": [types.Part.from_text(text=system_instruction_text)],
            "temperature": 1,
            "top_p": 0.9,
            "max_output_tokens": self.default_max_tokens,
            "thinking_config": types.ThinkingConfig(
                thinking_budget=self.default_thinking_budget
            ),
            "safety_settings": self.default_safety_settings
        }
        generation_config = types.GenerateContentConfig(**config)

        try:
            # Enforce rate limit
            current_time = time.time()
            time_elapsed = current_time - self.last_call_time
            if time_elapsed < self.min_time_between_calls:
                sleep_duration = self.min_time_between_calls - time_elapsed
                logging.info(f"Rate limit hit. Sleeping for {sleep_duration:.2f} seconds.")
                time.sleep(sleep_duration)
            self.last_call_time = time.time()

            # Rotate API key and reinitialize client
            self.client = self._initialize_client()

            response = self.client.models.generate_content(
                model=self.default_model_name,
                contents=contents,
                config=generation_config
            )
            
            if response.text:
                return response.text

            logging.warning(f"LLM returned empty response for instruction: '{instruction[:80]}...'")
            return "The air is thick with silence."

        except Exception as e:
            logging.error(f"Unexpected error for instruction: '{instruction[:80]}...'. Error: {e}")
            logging.error(traceback.format_exc()) # Log the full stack trace
            return f"An unexpected error occurred: {e}"
