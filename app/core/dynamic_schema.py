from typing import List, Type, Union, Annotated # Added Annotated
from pydantic import BaseModel, Field, create_model
from app.io.schemas import TurnPlan

def create_dynamic_turn_plan_model(tool_models: List[Type[BaseModel]]) -> Type[TurnPlan]:
    """
    Dynamically creates a Pydantic TurnPlan model with tool_calls strictly typed
    to a discriminated union of the provided tool_models.
    """
    if not tool_models:
        # If no tools are available, the tool_calls list should be empty.
        # We create a TurnPlan that explicitly forbids any tool calls.
        DynamicTurnPlan = create_model(
            "DynamicTurnPlan",
            thought=(str, ...),
            tool_calls=(List[BaseModel], Field(default_factory=list, description="No tools are available in this context.")),
            __base__=TurnPlan
        )
        return DynamicTurnPlan

    # Create a discriminated union of all available tool models
    # The 'name' field in each tool model will act as the discriminator
    DiscriminatedToolUnion = Union[tuple(tool_models)]
    
    # Apply the discriminator to the union type using Annotated
    AnnotatedUnion = Annotated[DiscriminatedToolUnion, Field(discriminator="name")]

    # Dynamically create a TurnPlan model using the discriminated union
    DynamicTurnPlan = create_model(
        "DynamicTurnPlan",
        thought=(str, ...),
        tool_calls=(List[AnnotatedUnion], Field(default_factory=list)), # Discriminator applied to AnnotatedUnion
        __base__=TurnPlan
    )
    return DynamicTurnPlan
