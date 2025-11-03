from typing import List
from app.io.schemas import TurnPlan
from app.models.message import Message
from app.llm.llm_connector import LLMConnector

class PlannerService:
    def __init__(self, llm: LLMConnector):
        self.llm = llm

    def plan(self, context_text: str, chat_history: List[Message]) -> TurnPlan | None:
        try:
            plan_dict = self.llm.get_structured_response(
                system_prompt=context_text,
                chat_history=chat_history,
                output_schema=TurnPlan
            )
            return TurnPlan.model_validate(plan_dict) if plan_dict is not None else None
        except Exception:
            return None
