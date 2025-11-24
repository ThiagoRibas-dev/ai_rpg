import os
import json
import openai
from typing import Dict, Type, List, Generator, Any
from pydantic import BaseModel, ValidationError
from app.llm.llm_connector import LLMConnector, LLMResponse
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
    ) -> List[Dict[str, Any]]:
        messages = []
        for msg in chat_history:
            message_dict = {"role": msg.role}
            
            # Handle Content (allow None if it's a pure tool call)
            if msg.content is not None:
                message_dict["content"] = msg.content
            
            # Handle Assistant Tool Calls
            if msg.role == "assistant" and msg.tool_calls:
                # Convert our internal normalized format back to OpenAI API format
                openai_tool_calls = []
                for tc in msg.tool_calls:
                    openai_tool_calls.append({
                        "id": tc.get("id", "call_unknown"),
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["arguments"]) if isinstance(tc["arguments"], dict) else tc["arguments"]
                        }
                    })
                message_dict["tool_calls"] = openai_tool_calls
                
                # OpenAI sometimes requires content to be null if missing
                if "content" not in message_dict:
                    message_dict["content"] = None

            # Handle Tool Results
            if msg.role == "tool":
                if not msg.tool_call_id:
                    # Fallback for legacy messages or errors
                    logger.warning("Message with role 'tool' missing 'tool_call_id'.")
                    message_dict["tool_call_id"] = "unknown_call_id"
                else:
                    message_dict["tool_call_id"] = msg.tool_call_id
                
                # Some local servers (and OpenAI) allow/expect 'name'
                if msg.name:
                    message_dict["name"] = msg.name

            messages.append(message_dict)
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
        temperature: float = 0.7,
        top_p: float = 0.9,
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
            temperature=temperature,
            top_p=top_p,
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
            return validated

        except ValidationError as e:
            logger.error(f"Validation error in OpenAI response: {e}", exc_info=True)
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
        """Legacy method kept for compatibility, delegates to standard chat."""
        # ... implementation skipped as we use chat_with_tools now ...
        return []

    def _clean_schema(self, schema: Dict[str, Any]):
        """
        Recursively remove 'title' and 'default' fields from JSON schema.
        """
        if isinstance(schema, dict):
            schema.pop("title", None)
            schema.pop("default", None)
            for value in schema.values():
                self._clean_schema(value)
        elif isinstance(schema, list):
            for item in schema:
                self._clean_schema(item)

    def chat_with_tools(
        self,
        system_prompt: str,
        chat_history: List[Message],
        tools: List[Dict[str, Any]],
    ) -> LLMResponse:
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self._convert_chat_history_to_messages(chat_history))

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto" if tools else None,
            temperature=0.7,
        )

        message = response.choices[0].message
        tool_calls_data = []

        if message.tool_calls:
            for tool_call in message.tool_calls:
                try:
                    tool_calls_data.append({
                        "name": tool_call.function.name,
                        "arguments": json.loads(tool_call.function.arguments),
                        "id": tool_call.id
                    })
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode arguments for {tool_call.function.name}")

        return LLMResponse(
            content=message.content,
            tool_calls=tool_calls_data if tool_calls_data else None
        )
