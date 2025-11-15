from pydantic import BaseModel, Field
from typing import List, Any, Literal, Optional


class PropertyDefinition(BaseModel):
    name: str = Field(
        ..., description="The programmatic name of the property (e.g., 'Sanity')."
    )
    type: Literal["integer", "string", "boolean", "enum", "resource"] = Field(
        ..., description="The data type of the property."
    )
    description: str = Field(
        ..., description="A human-readable description of what the property represents."
    )
    default_value: Any = Field(
        ...,
        description="The initial value for this property when an entity is created.",
    )

    has_max: bool = Field(
        False, description="For 'resource' types, indicates if there's a maximum value."
    )
    min_value: Optional[int] = Field(
        None,
        description="Minimum allowed integer value for 'integer' or 'resource' types.",
    )
    max_value: Optional[int] = Field(
        None,
        description="Maximum allowed integer value for 'integer' or 'resource' types.",
    )
    allowed_values: Optional[List[str]] = Field(
        None, description="For 'enum' types, a list of allowed string values."
    )

    display_category: str = Field(
        "Custom", description="Category for UI display (e.g., 'Resources', 'Stats')."
    )
    icon: Optional[str] = Field(
        None, description="An emoji or short string to use as an icon in the UI."
    )
    display_format: Literal["number", "bar", "badge"] = Field(
        "number", description="How the property should be displayed in the UI."
    )

    regenerates: bool = Field(
        False,
        description="For 'resource' types, indicates if the property regenerates over time.",
    )
    regeneration_rate: Optional[int] = Field(
        None,
        description="For 'resource' types, the rate at which it regenerates per game turn.",
    )

    # @validator("min_value", "max_value", pre=True, always=True)
    # def validate_min_max_values(cls, v, values):
    #     # Check if 'type' is already in values, otherwise skip validation for now
    #     if (
    #         "type" in values
    #         and v is not None
    #         and values["type"] not in ["integer", "resource"]
    #     ):
    #         raise ValueError(
    #             "min_value/max_value is only applicable for 'integer' or 'resource' types."
    #         )
    #     return v

    # @validator("max_value")
    # def validate_min_less_than_max(cls, v, values):
    #     if (
    #         v is not None
    #         and values.get("min_value") is not None
    #         and v < values["min_value"]
    #     ):
    #         raise ValueError("max_value must be greater than or equal to min_value")
    #     return v

    # @validator("allowed_values", pre=True, always=True)
    # def validate_allowed_values(cls, v, values):
    #     if "type" in values:
    #         if v is not None:  # Only validate if a value is provided
    #             if values["type"] != "enum":
    #                 raise ValueError(
    #                     "allowed_values is only applicable for 'enum' types."
    #                 )
    #             if values["type"] == "enum" and not v:
    #                 raise ValueError(
    #                     "For 'enum' type, allowed_values must not be empty."
    #                 )
    #     return v

    # @validator("regeneration_rate", pre=True, always=True)
    # def validate_regeneration_rate(cls, v, values):
    #     if "regenerates" in values:
    #         if v is not None and not values["regenerates"]:
    #             raise ValueError(
    #                 "regeneration_rate can only be set if 'regenerates' is True."
    #             )
    #         if values["regenerates"] and v is None:
    #             raise ValueError(
    #                 "regeneration_rate must be set if 'regenerates' is True."
    #             )
    #     return v
