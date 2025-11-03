from typing import Any, Dict
from app.models.property_definition import PropertyDefinition

PROPERTY_TEMPLATES: Dict[str, PropertyDefinition] = {
    "resource": PropertyDefinition(
        name="", # Name will be overridden
        type="resource",
        description="A quantifiable attribute that can be gained, lost, and potentially regenerated.",
        default_value=0,
        has_max=True,
        min_value=0,
        max_value=None, # Explicitly set to None
        allowed_values=None, # Explicitly set to None
        display_category="Resources",
        icon=None, # Explicitly set to None
        display_format="bar",
        regenerates=False, # Explicitly set to False
        regeneration_rate=None # Explicitly set to None
    ),
    "stat": PropertyDefinition(
        name="", # Name will be overridden
        type="integer",
        description="A core ability score, typically influencing skill checks or combat.",
        default_value=10,
        has_max=False, # Explicitly set to False
        min_value=1,
        max_value=20,
        allowed_values=None, # Explicitly set to None
        display_category="Stats",
        icon=None, # Explicitly set to None
        display_format="number",
        regenerates=False, # Explicitly set to False
        regeneration_rate=None # Explicitly set to None
    ),
    "reputation": PropertyDefinition(
        name="", # Name will be overridden
        type="integer",
        description="Standing with a faction or group, influencing interactions.",
        default_value=0,
        has_max=False, # Explicitly set to False
        min_value=-100,
        max_value=100,
        allowed_values=None, # Explicitly set to None
        display_category="Social",
        icon=None, # Explicitly set to None
        display_format="badge",
        regenerates=False, # Explicitly set to False
        regeneration_rate=None # Explicitly set to None
    ),
    "flag": PropertyDefinition(
        name="", # Name will be overridden
        type="boolean",
        description="A binary state indicating a condition or status.",
        default_value=False,
        has_max=False, # Explicitly set to False
        min_value=None, # Explicitly set to None
        max_value=None, # Explicitly set to None
        allowed_values=None, # Explicitly set to None
        display_category="Conditions",
        icon=None, # Explicitly set to None
        display_format="badge",
        regenerates=False, # Explicitly set to False
        regeneration_rate=None # Explicitly set to None
    ),
    "enum": PropertyDefinition(
        name="", # Name will be overridden
        type="enum",
        description="A property with a predefined set of string values.",
        default_value="",
        has_max=False, # Explicitly set to False
        min_value=None, # Explicitly set to None
        max_value=None, # Explicitly set to None
        allowed_values=None, # Changed to None to avoid validation error on template definition
        display_category="Status",
        icon=None, # Explicitly set to None
        display_format="badge",
        regenerates=False, # Explicitly set to False
        regeneration_rate=None # Explicitly set to None
    ),
    "string": PropertyDefinition(
        name="", # Name will be overridden
        type="string",
        description="A free-form text property.",
        default_value="",
        has_max=False, # Explicitly set to False
        min_value=None, # Explicitly set to None
        max_value=None, # Explicitly set to None
        allowed_values=None, # Explicitly set to None
        display_category="Details",
        icon=None, # Explicitly set to None
        display_format="badge",
        regenerates=False, # Explicitly set to False
        regeneration_rate=None # Explicitly set to None
    )
}

def apply_template(template_name: str, overrides: Dict[str, Any]) -> PropertyDefinition:
    """
    Applies a template to create a PropertyDefinition, merging with provided overrides.
    """
    template = PROPERTY_TEMPLATES.get(template_name)
    if not template:
        raise ValueError(f"Unknown property template: {template_name}")
    
    # Create a copy of the template and update with overrides
    template_dict = template.model_dump()
    template_dict.update(overrides)
    
    return PropertyDefinition(**template_dict)
