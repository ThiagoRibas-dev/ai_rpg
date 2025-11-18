import os
import json
import openai
from typing import Dict, Type, List, Generator, Any
from pydantic import BaseModel, ValidationError
from app.llm.llm_connector import LLMConnector
from app.models.message import Message
import logging

logger = logging.getLogger(__name__)


class OpenAIConnector(LLMConnector):
    """
    Reference : https://deepwiki.com/openai/openai-python/4.1-chat-completions-api
    """

    def __init__(self):
        self.base_url = os.environ.get("OPENAI_API_BASE_URL")
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.model = os.environ.get("OPENAI_API_MODEL")
        if not self.base_url:
            logger.error("OPENAI_API_BASE_URL environment variable not set.")
            raise ValueError("OPENAI_API_BASE_URL environment variable not set.")
        if not self.api_key:
            logger.error("OPENAI_API_KEY environment variable not set.")
            raise ValueError("OPENAI_API_KEY environment variable not set.")
        if not self.model:
            logger.error("OPENAI_API_MODEL environment variable not set.")
            raise ValueError("OPENAI_API_MODEL environment variable not set.")
        self.client = openai.OpenAI(base_url=self.base_url, api_key=self.api_key)

    def _convert_chat_history_to_messages(
        self, chat_history: List[Message]
    ) -> List[Dict[str, str]]:
        messages = []
        for msg in chat_history:
            messages.append({"role": msg.role, "content": msg.content})
        return messages

    def get_streaming_response(
        self, system_prompt: str, chat_history: List[Message]
    ) -> Generator[str, None, None]:
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self._convert_chat_history_to_messages(chat_history))

        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
        )
        for chunk in stream:
            if (
                chunk.choices
                and chunk.choices[0].delta
                and chunk.choices[0].delta.content
            ):
                yield chunk.choices[0].delta.content

    def get_structured_response(
        self,
        system_prompt: str,
        chat_history: List[Message],
        output_schema: Type[BaseModel],
    ) -> BaseModel:
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self._convert_chat_history_to_messages(chat_history))

        # Generate and clean the schema to satisfy strict backends
        json_schema = output_schema.model_json_schema()
        self._clean_schema(json_schema)

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_completion_tokens=-1,
            temperature=0.7,
            top_p=0.9,
            response_format={
                "type": "json_object",
                "schema": json_schema,
            },
            extra_body={
                "chat_template_kwargs": {"enable_thinking": False},
                "top_k": 40,
                "response_format": {
                    "type": "json_object",
                    "schema": json_schema,
                },
            },
        )

        content = resp.choices[0].message.content

        try:
            # Parse and validate
            validated = output_schema.model_validate_json(content)

            # Extra check for TurnPlan - log if tool_calls were filtered
            if hasattr(validated, "tool_calls"):
                logger.debug(
                    f"Validated response with {len(validated.tool_calls)} tool calls"
                )

            return validated

        except ValidationError as e:
            logger.error(f"Validation error in OpenAI response: {e}", exc_info=True)
            logger.error(f"Raw content: {content}")
            logger.error(f"Schema: {output_schema.__name__}")

            # Try to parse as dict to see what we got
            try:
                parsed = json.loads(content)
                logger.error(f"Parsed as dict: {parsed}")
            except json.JSONDecodeError:  # Specify the exception type
                logger.error(
                    "Failed to parse raw content as dict after initial JSON decode error."
                )
                pass

            raise

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in OpenAI response: {e}", exc_info=True)
            logger.error(f"Raw content: {content}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred in get_structured_response: {e}", exc_info=True)
            logger.error(f"Raw content: {content}")
            raise

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in OpenAI response: {e}", exc_info=True)
            logger.error(f"Raw content: {content}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred in get_structured_response: {e}", exc_info=True)
            logger.error(f"Raw content: {content}")
            raise

    def get_tool_calls(
        self,
        system_prompt: str,
        chat_history: List[Message],
        tools: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Makes an OpenAI-compatible API call and returns a list of tool calls."""
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self._convert_chat_history_to_messages(chat_history))

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            max_completion_tokens=-1,
            temperature=0.7,
            top_p=0.9,
            tool_choice="auto",
            extra_body={
                "chat_template_kwargs": {"enable_thinking": False},
                "top_k": 40,
            },
        )

        response_message = response.choices[0].message
        tool_calls_data = []

        if response_message.tool_calls:
            for tool_call in response_message.tool_calls:
                try:
                    tool_calls_data.append(
                        {
                            "name": tool_call.function.name,
                            "arguments": json.loads(tool_call.function.arguments),
                        }
                    )
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode tool call arguments for {tool_call.function.name}: {e}", exc_info=True)
                    # Optionally, append an error entry or skip this tool call
                    tool_calls_data.append(
                        {
                            "name": tool_call.function.name,
                            "arguments": {},
                            "error": f"Failed to parse arguments: {e}"
                        }
                    )

        return tool_calls_data

    def _clean_schema(self, schema: Dict[str, Any]):
        """
        Recursively remove 'title' and 'default' fields from JSON schema.
        This is necessary because some local LLM servers (like llama.cpp) fail to parse
        schemas that contain metadata fields without explicit types, or strict defaults.
        """
        if isinstance(schema, dict):
            schema.pop("title", None)
            schema.pop("default", None)
            for value in schema.values():
                self._clean_schema(value)
        elif isinstance(schema, list):
            for item in schema:
                self._clean_schema(item)