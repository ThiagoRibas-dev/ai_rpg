from typing import List, Type, Union, Annotated # Added Annotated
from pydantic import BaseModel, Field, create_model, field_validator
from app.io.schemas import TurnPlan
import logging

logger = logging.getLogger(__name__)

def create_dynamic_turn_plan_model(tool_models: List[Type[BaseModel]]) -> Type[TurnPlan]:
    """
    Dynamically creates a Pydantic TurnPlan model with tool_calls strictly typed
    to a discriminated union of the provided tool_models.
    """
    if not tool_models:
        # If no tools are available, the tool_calls list should be empty.
        # If no tools are available, the tool_calls list should be empty.
        # We create a TurnPlan that explicitly forbids any tool calls.
        DynamicTurnPlan = create_model(
            "DynamicTurnPlan",
            thought=(str, ...),
            tool_calls=(List[BaseModel], Field(
                default_factory=lambda: [], 
                description="No tools are available in this context.",
                max_items=0
            )),
            __base__=TurnPlan
        )
        return DynamicTurnPlan

    # Create a discriminated union of all available tool models
    # The 'name' field in each tool model will act as the discriminator
    DiscriminatedToolUnion = Union[tuple(tool_models)]
    
    # Apply the discriminator to the union type using Annotated
    AnnotatedUnion = Annotated[DiscriminatedToolUnion, Field(discriminator="name")]

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
            if not hasattr(call, 'name'):
                logger.warning(f"Tool call {i} has no 'name' attribute - skipping")
                continue
            
            valid_calls.append(call)
        
        if len(valid_calls) != len(tool_calls):
            logger.warning(f"Filtered tool_calls: {len(tool_calls)} → {len(valid_calls)} valid")
        
        return valid_calls

    # Dynamically create a TurnPlan model using the discriminated union
    DynamicTurnPlan = create_model(
        "DynamicTurnPlan",
        thought=(str, ...),
        tool_calls=(List[AnnotatedUnion], Field(default_factory=lambda: [])),
        __base__=TurnPlan,
        __validators__={
            'validate_tool_calls': field_validator('tool_calls')(validate_tool_calls)
        }
    )
    
    # Log available tool names for debugging
    tool_names = [model.model_fields["name"].default for model in tool_models]
    logger.debug(f"Created DynamicTurnPlan with {len(tool_models)} tools: {tool_names}")
    
    return DynamicTurnPlan
