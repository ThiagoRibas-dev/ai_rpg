import os
import json
import time
import logging
import traceback
import requests
from pydantic import ValidationError, create_model, Field
from typing import Optional

from app.llm.prompts import GameLoopPrompts
from app.schemas.wrapper_schemas import DualResponse
from app.schemas.action_request import ActionRequest


class OpenAIConnector:
    """
    A class to handle communication with OpenAI-compatible APIs.
    """

    def __init__(self):
        """
        Initializes the OpenAIConnector, configuring the API client.
        """
        self.base_url = os.environ.get("OPENAI_API_BASE_URL", "http://localhost:8080")
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.default_model_name = os.environ.get("OPENAI_API_MODEL", "gpt-3.5-turbo")

    def generate_structured_response(
        self,
        action_request: ActionRequest,
        max_retries: int = 0,
        retry_prompt: Optional[str] = None
    ) -> DualResponse:
        """
        Generates a dual response containing both a conversational chat reply and
        structured JSON data from an OpenAI-compatible API.
        """
        instruction = action_request.instruction
        chat_history = action_request.chat_history
        response_schema = action_request.response_schema
        context_data = action_request.context_data

        DynamicDualResponse = create_model(
            'DynamicDualResponse',
            __base__=DualResponse,
            generated_data=(response_schema, Field(description="The structured data requested."))
        )

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        for attempt in range(max_retries):
            try:
                messages = []

                # System message with context and instruction
                system_content = ("# D&D 3.5e Game.\n"
                                " - Dungeon Master's Personality : Professional (Analytical, detail oriented, direct);\n"
                                " - Dungeon Master's Prose : Brandon Sanderson (Straightforward and functional);\n"
                                "Adapt Personality and Prose to the campaign's tone and themes.\n\n")
                if context_data:
                    system_content += f"{context_data}\n"
                system_content += instruction
                # system_content += "\nYou must provide a conversational reply."
                messages.append({"role": "system", "content": system_content})

                # Chat history
                for message in chat_history:
                    role = "user" if message.role == "user" else "assistant"
                    messages.append({"role": role, "content": message.content})
                
                if attempt > 0:
                    messages.append({"role": "user", "content": retry_prompt or GameLoopPrompts.RETRY_WITH_INSTRUCTIONS})

                payload = {
                    "model": self.default_model_name,
                    "messages": messages,
                    "n_predict": -1, # Max tokens to generate
                    "temperature": 0.7,
                    "top_k": 40,
                    "top_p": 0.9,
                    "response_format": {
                        "type": "json_object",
                        "schema": DynamicDualResponse.model_json_schema()
                    }
                }

                response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                response.raise_for_status() # Raise an exception for HTTP errors

                response_data = response.json()
                
                # Extract chat reply and structured data
                chat_reply = ""
                generated_json = {}

                if response_data and response_data.get("choices"):
                    message_content = response_data["choices"][0]["message"].get("content", "")
                    try:
                        parsed_content = json.loads(message_content)
                        chat_reply = parsed_content.get("chat_reply", "")
                        generated_json = parsed_content.get("generated_data", {})
                    except json.JSONDecodeError:
                        logging.warning("Could not decode JSON from message content, treating as plain text.")
                        chat_reply = message_content # Fallback to full content as chat reply

                if generated_json:
                    try:
                        validated_response = DynamicDualResponse(chat_reply=chat_reply, generated_data=generated_json)
                        return validated_response
                    except ValidationError as e:
                        logging.error(f"Validation error for OpenAI response on attempt {attempt + 1}/{max_retries}: {e}")
                        if attempt == max_retries - 1:
                            logging.error(traceback.format_exc())
                            return DualResponse(chat_reply=f"An error occurred after multiple retries: {e}", generated_data={"error": f"Failed to validate LLM JSON. Raw text: {message_content}."})
                        time.sleep(30)
                else:
                    logging.warning(f"No valid JSON found in OpenAI response on attempt {attempt + 1}/{max_retries}. Response: {message_content[:100]}...")
                    if attempt == max_retries - 1:
                        return DualResponse(chat_reply=chat_reply, generated_data={"error": "No structured data generated."} )
                    time.sleep(30)

            except requests.exceptions.RequestException as e:
                logging.error(f"Network error with OpenAI API on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt == max_retries - 1:
                    logging.error(traceback.format_exc())
                    return DualResponse(chat_reply=f"An error occurred with the OpenAI API: {e}", generated_data={"error": str(e)})
                time.sleep(30)
            except json.JSONDecodeError as e:
                logging.error(f"JSON decode error from OpenAI API on attempt {attempt + 1}/{max_retries}: {e}. Response: {response.text[:100]}...")
                if attempt == max_retries - 1:
                    logging.error(traceback.format_exc())
                    return DualResponse(chat_reply=f"An error occurred parsing OpenAI API response: {e}", generated_data={"error": str(e)})
                time.sleep(30)
            except Exception as e:
                logging.error(f"Unexpected error in OpenAIConnector on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt == max_retries - 1:
                    logging.error(traceback.format_exc())
                    return DualResponse(chat_reply=f"An unexpected error occurred: {e}", generated_data={"error": str(e)})
                time.sleep(30)

        error_message = f"OpenAI API returned no valid content after {max_retries} retries for instruction: '{instruction[:80]}...'"
        logging.error(error_message)
        return DualResponse(chat_reply=error_message, generated_data={"error": error_message})

    def generate_chat_response(self, action_request: ActionRequest) -> str:
        """
        Generates a conversational response from an OpenAI-compatible API.
        """
        instruction = action_request.instruction
        chat_history = action_request.chat_history
        context_data = action_request.context_data

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            messages = []

            # System message with context and instruction
            system_content = ("# D&D 3.5e Game.\n"
                             "Dungeon Master personality : Default - Professional."
                             "Will addapt to the campaign's tone and themes.\n\n")
            if context_data:
                system_content += f"{context_data}\n"
            system_content += instruction
            # system_content += "\nYou must provide a conversational reply."
            messages.append({"role": "system", "content": system_content})

            # Chat history
            for message in chat_history:
                role = "user" if message.role == "user" else "assistant"
                messages.append({"role": role, "content": message.content})

            payload = {
                "model": self.default_model_name,
                "messages": messages,
                "n_predict": -1, # Max tokens to generate
                "temperature": 0.7,
                "top_k": 40,
                "top_p": 0.9
            }

            response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status() # Raise an exception for HTTP errors

            response_data = response.json()

            if response_data and response_data.get("choices"):
                message_content = response_data["choices"][0]["message"].get("content", "")
                return message_content

            logging.warning(f"LLM returned empty response for instruction: '{instruction[:80]}...'")
            return "The air is thick with silence."

        except requests.exceptions.RequestException as e:
            logging.error(f"Network error with OpenAI API: {e}")
            return f"An error occurred with the OpenAI API: {e}"
        except Exception as e:
            logging.error(f"Unexpected error in OpenAIConnector: {e}")
            logging.error(traceback.format_exc())
            return f"An unexpected error occurred: {e}"