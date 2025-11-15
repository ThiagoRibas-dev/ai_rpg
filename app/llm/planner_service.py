import logging
from typing import List
from pydantic import BaseModel
from app.llm.schemas import PlayerIntentAnalysis, StrategicPlan
from app.models.message import Message
from app.llm.llm_connector import LLMConnector

logger = logging.getLogger(__name__)


class PlannerService:
    def __init__(self, llm: LLMConnector):
        self.llm = llm

    def analyze_intent(
        self,
        system_instruction: str,
        phase_template: str,
        chat_history: List[Message],
    ) -> PlayerIntentAnalysis | None:
        """Phase 1: Determine the player's core intent."""
        prefill = f"\n{phase_template}\n\nMy analysis of the player's intent is:"
        prefilled_history = chat_history + [Message(role="assistant", content=prefill)]
        try:
            return self.llm.get_structured_response(
                system_prompt=system_instruction,
                chat_history=prefilled_history,
                output_schema=PlayerIntentAnalysis,
            )
        except Exception as e:
            logger.error(f"Error in PlannerService.analyze_intent: {e}", exc_info=True)
            return None

    def develop_strategy(
        self,
        system_instruction: str,
        phase_template: str,
        analysis: str,
        dynamic_context: str,
        chat_history: List[Message],
    ) -> StrategicPlan | None:
        """Phase 2: Formulate a high-level plan and narrative goal."""
        prefill = f"""[Player Intent Analysis]
{analysis}

{phase_template}
{dynamic_context}

My strategic plan is:"""
        prefilled_history = chat_history + [Message(role="assistant", content=prefill)]
        try:
            return self.llm.get_structured_response(
                system_prompt=system_instruction,
                chat_history=prefilled_history,
                output_schema=StrategicPlan,
            )
        except Exception as e:
            logger.error(f"Error in PlannerService.develop_strategy: {e}", exc_info=True)
            return None

    def select_tools(
        self,
        system_instruction: str,
        phase_template: str,
        strategic_plan: StrategicPlan,
        chat_history: List[Message],
        tool_registry, # Pass the whole registry
        available_tool_names: List[str],
    ) -> List[BaseModel]:
        """Phase 3: Select concrete tools to execute the strategic plan."""
        narrative_plan = strategic_plan.response_plan
        plan_steps_str = "\n - ".join(strategic_plan.plan_steps)
        prefill = f"""{phase_template}\n\nMy analysis of the current exchange:\n{narrative_plan}\n\nStep by step plan:\n - {plan_steps_str}\n\n"""
        
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
            name_to_type_map = {tool_type.model_fields['tool_name'].default: tool_type for tool_type in tool_registry.get_all_tool_types()}
            for call in api_tool_calls:
                tool_name = call.get("name")
                if tool_name in name_to_type_map:
                    model_class = name_to_type_map[tool_name]
                    instance = model_class(**call.get("arguments", {}))
                    pydantic_tool_calls.append(instance)
            
            logger.debug(f"Tool selection phase produced {len(pydantic_tool_calls)} tool calls.")
            return pydantic_tool_calls
            
        except Exception as e:
            logger.error(f"Error in PlannerService.select_tools: {e}", exc_info=True)
            return []
