from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, create_model
from app.io.schemas import TurnPlan # Keep for base structure, but will dynamically create
from app.models.message import Message
from app.llm.llm_connector import LLMConnector

class PlannerService:
    def __init__(self, llm: LLMConnector):
        self.llm = llm

    def plan(self, context_text: str, chat_history: List[Message], available_tool_schemas: List[Dict[str, Any]]) -> TurnPlan | None:
        # Extract tool names for Literal type
        tool_names = [schema["name"] for schema in available_tool_schemas]
        
        # Dynamically create a TurnPlan model.
        # If no tools are available, the 'tool_calls' field will be an empty list.
        # Otherwise, it will be a list of dynamically constrained ToolCall models.
        
        if not tool_names:
            # If no tools are available, the LLM cannot call any tools.
            # We define tool_calls as an empty list to prevent any tool calls.
            DynamicTurnPlan = create_model(
                "DynamicTurnPlan",
                thought=(str, ...),
                tool_calls=(List[Any], Field(default_factory=list)), # Use Any to allow empty list
                __base__=BaseModel
            )
        else:
            # Create a Literal type from available tool names
            DynamicToolName = Literal[tuple(tool_names)]

            # Dynamically create a ToolCall model with constrained 'name'
            DynamicToolCall = create_model(
                "DynamicToolCall",
                name=(DynamicToolName, ...),
                arguments=(Optional[str], None),
                __base__=BaseModel
            )

            # Dynamically create a TurnPlan model using the DynamicToolCall
            DynamicTurnPlan = create_model(
                "DynamicTurnPlan",
                thought=(str, ...),
                tool_calls=(List[DynamicToolCall], Field(default_factory=list)),
                __base__=BaseModel
            )

        try:
            plan_dict = self.llm.get_structured_response(
                system_prompt=context_text,
                chat_history=chat_history,
                output_schema=DynamicTurnPlan # Use the dynamically created schema
            )
            return DynamicTurnPlan.model_validate(plan_dict) if plan_dict is not None else None
        except Exception as e:
            # Log the exception for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in PlannerService.plan: {e}", exc_info=True)
            return None
