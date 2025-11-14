import logging
from typing import List, Type, Union
from pydantic import BaseModel, Field, create_model, field_validator
from app.llm.schemas import ToolCall

logger = logging.getLogger(__name__)


def create_dynamic_turn_plan_model(
    tool_models: List[Type[BaseModel]],
) -> Type[BaseModel]:
    """
    Dynamically creates a Pydantic model for tool selection, including
    tool_calls strictly typed to a discriminated union of the provided tool_models.
    """
    # If no tools are available, the tool_calls list should be empty.
    # We create a model that explicitly forbids any tool calls.
    if not tool_models:
        DynamicExecutionPlan = create_model(
            "DynamicExecutionPlan",
            tool_calls=(
                List[ToolCall],
                Field(
                    default_factory=list,
                    description="No tools are available in this context.",
                ),
            ),
        )
        return DynamicExecutionPlan

    # ✅ Create validator to filter out invalid tool calls
    def validate_tool_calls(cls, tool_calls):
        """Filter out any invalid tool calls (empty objects, missing name, etc.)"""
        valid_calls = []
        for i, call in enumerate(tool_calls):
            # Check if it's a raw BaseModel (validation failed)
            if type(call) is BaseModel:
                logger.warning(f"Tool call {i} is raw BaseModel - skipping")
                continue

            # Check if it has a name attribute
            if not hasattr(call, "name"):
                logger.warning(f"Tool call {i} has no 'name' attribute - skipping")
                continue

            valid_calls.append(call)

        if len(valid_calls) != len(tool_calls):
            logger.warning(
                f"Filtered tool_calls: {len(tool_calls)} → {len(valid_calls)} valid"
            )

        return valid_calls

    # Dynamically create an ExecutionPlan model using the discriminated union
    DynamicExecutionPlan = create_model(
        "DynamicExecutionPlan",
        tool_calls=(
            List[Union[*tool_models]], # Corrected Union unpacking
            Field(
                ...,
                description="The tools that will be executed based on the input analysis and the response plan.",
            ),
        ),
        __validators__={
            "validate_tool_calls": field_validator("tool_calls")(validate_tool_calls)
        },
    )

    # Log available tool names for debugging
    logger.debug(f"Created DynamicExecutionPlan : {DynamicExecutionPlan.schema_json()}\n")

    return DynamicExecutionPlan
