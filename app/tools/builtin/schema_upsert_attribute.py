import logging
from typing import Any, Dict, Optional, List, Literal
from app.models.property_definition import PropertyDefinition
from app.tools.builtin.property_templates import apply_template

logger = logging.getLogger(__name__)


def handler(
    property_name: str,
    description: str,
    entity_type: Literal[
        "character", "item", "location"
    ] = "character",
    template: Optional[str] = None,
    type: Optional[Literal["integer", "string", "boolean", "enum", "resource"]] = None,
    default_value: Any = None,
    has_max: Optional[bool] = None,
    min_value: Optional[int] = None,
    max_value: Optional[int] = None,
    allowed_values: Optional[List[str]] = None,
    display_category: Optional[str] = None,
    icon: Optional[str] = None,
    display_format: Optional[Literal["number", "bar", "badge"]] = None,
    regenerates: Optional[bool] = None,
    regeneration_rate: Optional[int] = None,
    **context: Any,
) -> Dict[str, Any]:
    """
    Allows the AI to define a new custom attribute (property) for game entities.
    These properties extend the core schema and are used to create dynamic game mechanics.

    Args:
        property_name (str): The programmatic name of the property (e.g., 'Sanity', 'Mana').
        description (str): A human-readable description of what the property represents.
        entity_type (Literal["character", "item", "location"]): The type of entity this property applies to.
        template (Optional[str]): A predefined template to use (e.g., 'resource', 'stat', 'reputation', 'flag', 'enum', 'string').
                                  If provided, other parameters will override template defaults.
        type (Optional[Literal["integer", "string", "boolean", "enum", "resource"]]): The data type of the property. Required if no template is used.
        default_value (Any): The initial value for this property. Required if no template is used.
        has_max (Optional[bool]): For 'resource' types, indicates if there's a maximum value.
        min_value (Optional[int]): Minimum allowed integer value for 'integer' or 'resource' types.
        max_value (Optional[int]): Maximum allowed integer value for 'integer' or 'resource' types.
        allowed_values (Optional[List[str]]): For 'enum' types, a list of allowed string values.
        display_category (Optional[str]): Category for UI display (e.g., 'Resources', 'Stats').
        icon (Optional[str]): An emoji or short string to use as an icon in the UI.
        display_format (Optional[Literal["number", "bar", "badge"]]): How the property should be displayed in the UI.
        regenerates (Optional[bool]): For 'resource' types, indicates if the property regenerates over time.
        regeneration_rate (Optional[int]): For 'resource' types, the rate at which it regenerates per game turn.
        context (Any): The tool execution context, including session_id and db_manager.

    Returns:
        Dict[str, Any]: A dictionary indicating success and the defined property.
    """
    session_id = context.get("session_id")
    db_manager = context.get("db_manager")

    if not session_id or not db_manager:
        logger.error(
            "Session ID or DB Manager not found in context for schema.upsert_attibute."
        )
        return {"success": False, "error": "Missing session context."}

    overrides: Dict[str, Any] = {
        "property_name": property_name,
        "description": description,
        "default_value": default_value,
        "type": type,
        "has_max": has_max,
        "min_value": min_value,
        "max_value": max_value,
        "allowed_values": allowed_values,
        "display_category": display_category,
        "icon": icon,
        "display_format": display_format,
        "regenerates": regenerates,
        "regeneration_rate": regeneration_rate,
    }
    # Filter out None values from overrides
    overrides = {k: v for k, v in overrides.items() if v is not None}

    try:
        if template:
            prop_def = apply_template(template, overrides)
        else:
            # If no template, 'type' and 'default_value' are mandatory
            if "type" not in overrides or "default_value" not in overrides:
                raise ValueError(
                    "When no template is provided, 'type' and 'default_value' are required."
                )
            prop_def = PropertyDefinition(**overrides)

        # Save to DB
        db_manager.create_schema_extension(
            session_id, entity_type, property_name, prop_def.model_dump()
        )

        logger.info(f"Defined new property '{property_name}' for entity type '{entity_type}'.")
        return {"success": True, "property": prop_def.model_dump()}

    except ValueError as e:
        logger.error(f"Error defining property: {e}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        return {"success": False, "error": f"An unexpected error occurred: {e}"}
