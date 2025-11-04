from typing import List, Type
from pydantic import BaseModel
from app.io.schemas import TurnPlan
from app.models.message import Message
from app.llm.llm_connector import LLMConnector
from app.core.dynamic_schema import create_dynamic_turn_plan_model # New import

class PlannerService:
    def __init__(self, llm: LLMConnector):
        self.llm = llm

    def plan(self, context_text: str, chat_history: List[Message], available_tool_models: List[Type[BaseModel]]) -> TurnPlan | None:
        """
        Generates a TurnPlan using the LLM, with tool calls strictly validated
        against the provided Pydantic tool models.
        """
        # Dynamically create a TurnPlan model with a discriminated union of available tool models
        DynamicTurnPlan = create_dynamic_turn_plan_model(available_tool_models)

        try:
            plan_dict = self.llm.get_structured_response(
                system_prompt=context_text,
                chat_history=chat_history,
                output_schema=DynamicTurnPlan
            )
            return DynamicTurnPlan.model_validate(plan_dict) if plan_dict is not None else None
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in PlannerService.plan: {e}", exc_info=True)
            return None
