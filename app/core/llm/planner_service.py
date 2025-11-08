import logging
from typing import List, Type
from pydantic import BaseModel
from app.io.schemas import TurnPlan
from app.models.message import Message
from app.llm.llm_connector import LLMConnector
from app.core.dynamic_schema import create_dynamic_turn_plan_model

logger = logging.getLogger(__name__)


class PlannerService:
    def __init__(self, llm: LLMConnector):
        self.llm = llm

    def plan(
        self,
        system_instruction: str,
        phase_template: str,
        dynamic_context: str,
        chat_history: List[Message],
        available_tool_models: List[Type[BaseModel]],
    ) -> TurnPlan | None:
        """
        Generates a TurnPlan using the LLM with prompt caching optimization.
        """
        DynamicTurnPlan = create_dynamic_turn_plan_model(available_tool_models)

        # Build assistant prefill with dynamic content
        prefill = f"""
{phase_template}
{dynamic_context}

My Plan: 
"""

        # Inject prefill as final assistant message
        prefilled_history = chat_history + [Message(role="assistant", content=prefill)]

        try:
            # ✅ Connector now returns a validated instance
            plan = self.llm.get_structured_response(
                system_prompt=system_instruction,
                chat_history=prefilled_history,
                output_schema=DynamicTurnPlan,
            )

            # ✅ If no tool calls after validation, that's OK
            if plan and not plan.tool_calls:
                logger.debug("Plan has no tool calls (empty or filtered out)")

            return plan

        except Exception as e:
            logger.error(f"Error in PlannerService.plan: {e}", exc_info=True)
            return None
