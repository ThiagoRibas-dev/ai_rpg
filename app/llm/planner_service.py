import logging
from typing import List

from pydantic import BaseModel

from app.llm.llm_connector import LLMConnector
from app.llm.schemas import TurnPlan
from app.models.message import Message
from app.tools.schemas import (
    Deliberate,
)

logger = logging.getLogger(__name__)


class PlannerService:
    def __init__(self, llm: LLMConnector):
        self.llm = llm

    def create_plan(
        self,
        system_instruction: str,
        phase_template: str,
        dynamic_context: str,
        chat_history: List[Message],
    ) -> TurnPlan | None:
        """Phase 1: Combines analysis and strategic planning into a single step."""
        prefill = f"""{phase_template}\n\n{dynamic_context}\n\nHere is my analysis and plan:\n"""
        prefilled_history = chat_history + [Message(role="assistant", content=prefill)]
        try:
            return self.llm.get_structured_response(
                system_prompt=system_instruction,
                chat_history=prefilled_history,
                output_schema=TurnPlan,
            )
        except Exception as e:
            logger.error(f"Error in PlannerService.create_plan: {e}", exc_info=True)
            return None

    def select_tools(
        self,
        system_instruction: str,
        phase_template: str,
        analysis: str,
        plan_steps: List[str],
        chat_history: List[Message],
        tool_registry,  # Pass the whole registry
        available_tool_names: List[str],
    ) -> List[BaseModel]:
        """Phase 2: Select concrete tools to execute the strategic plan."""
        plan_steps_str = "\n - ".join(plan_steps)
        prefill = f"""{phase_template}\n\n{analysis}\n\nThe step-by-step plan is as follows:\n - {plan_steps_str}\n\nNow I'll choose the tools I will use to execute each step:\n"""

        prefilled_history = chat_history + [Message(role="assistant", content=prefill)]

        # Get the schemas for the available tools in the format the LLM API expects
        llm_tool_schemas = tool_registry.get_llm_tool_schemas(available_tool_names)

        try:
            # Use the new native tool calling method
            api_tool_calls = self.llm.get_tool_calls(
                system_prompt=system_instruction,
                chat_history=prefilled_history,
                tools=llm_tool_schemas,
            )

            # Convert the API response back into our Pydantic models for type-safe execution
            pydantic_tool_calls = []
            name_to_type_map = {
                tool_type.model_fields["name"].default: tool_type
                for tool_type in tool_registry.get_all_tool_types()
            }
            for call in api_tool_calls:
                tool_name = call.get("name")
                if tool_name in name_to_type_map:
                    model_class = name_to_type_map[tool_name]
                    instance = model_class(**call.get("arguments", {}))
                    pydantic_tool_calls.append(instance)

            logger.debug(
                f"Tool selection phase produced {len(pydantic_tool_calls)} tool calls."
            )
            return pydantic_tool_calls

        except Exception as e:
            logger.error(f"Error in PlannerService.select_tools: {e}", exc_info=True)
            return []

    def select_tools_for_step(
        self,
        system_instruction: str,
        phase_template: str,
        analysis: str,
        plan_step: str,
        chat_history: List[Message],
        tool_registry,
        available_tool_names: List[str],
    ) -> List[BaseModel]:
        """
        --- NEW ---
        Phase 2 (Iterative): Select a tool for a single step of the plan.
        """
        tool_names_for_prompt = ", ".join(available_tool_names)

        prompt_content = phase_template.format(
            analysis=analysis,
            tool_names_list=tool_names_for_prompt,
            plan_step=plan_step,
            deliberate_tool=Deliberate.model_fields["name"].default,
        )

        tool_selection_history = chat_history + [
            Message(role="assistant", content=prompt_content)
        ]

        llm_tool_schemas = tool_registry.get_llm_tool_schemas(available_tool_names)

        try:
            api_tool_calls = self.llm.get_tool_calls(
                system_prompt=system_instruction,
                chat_history=tool_selection_history,
                tools=llm_tool_schemas,
            )

            pydantic_tool_calls = []
            name_to_type_map = {
                tool_type.model_fields["name"].default: tool_type
                for tool_type in tool_registry.get_all_tool_types()
            }
            for call in api_tool_calls:
                tool_name = call.get("name")
                if tool_name in name_to_type_map:
                    model_class = name_to_type_map[tool_name]
                    instance = model_class(**call.get("arguments", {}))
                    pydantic_tool_calls.append(instance)
            return pydantic_tool_calls
        except Exception as e:
            logger.error(
                f"Error in PlannerService.select_tools_for_step: {e}", exc_info=True
            )
            return []
