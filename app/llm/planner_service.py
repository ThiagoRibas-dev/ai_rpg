import logging
from typing import List, Type
from pydantic import BaseModel
# MODIFIED: Import new schemas
from app.llm.schemas import PlayerIntentAnalysis, StrategicPlan
from app.models.message import Message
from app.llm.llm_connector import LLMConnector
from app.core.dynamic_schema import create_dynamic_turn_plan_model # We can rename this later if we want

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
        available_tool_models: List[Type[BaseModel]],
    ) -> List[BaseModel]:
        """Phase 3: Select concrete tools to execute the strategic plan."""
        # This is a bit of a workaround. We create a dynamic model that *only* contains the tool_calls field.
        # This reuses the existing discriminated union logic perfectly.
        
        DynamicExecutionPlan = create_dynamic_turn_plan_model(available_tool_models)

        narrative_plan = strategic_plan.response_plan
        plan_steps_str = "\n - ".join(strategic_plan.plan_steps)
        prefill = f"""{phase_template}\n\nMy analysis of the current exchange:\n{narrative_plan}\n\nStep by step plan:\n{plan_steps_str}\n\nStructured Tool Calls:\n"""
        
        prefilled_history = chat_history + [Message(role="assistant", content=prefill)]
        try:
            # We expect a model instance that contains the 'tool_calls' attribute
            execution_plan = self.llm.get_structured_response(
                system_prompt=system_instruction,
                chat_history=prefilled_history,
                output_schema=DynamicExecutionPlan,
            )
            if execution_plan and hasattr(execution_plan, 'tool_calls'):
                 logger.debug(f"Tool selection phase produced {len(execution_plan.tool_calls)} tool calls.")
                 return execution_plan.tool_calls
            return []
        except Exception as e:
            logger.error(f"Error in PlannerService.select_tools: {e}", exc_info=True)
            return []
