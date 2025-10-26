from pydantic import BaseModel, Field, create_model
from typing import List, Dict, Any, Optional, Type

def _inline_defs(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively inlines $ref definitions from $defs in a JSON schema.
    """
    if '$defs' not in schema:
        return schema

    defs = schema['$defs']

    def _resolve_refs(obj):
        if isinstance(obj, dict):
            if '$ref' in obj:
                ref_path = obj['$ref'].split('/')
                if len(ref_path) == 3 and ref_path[0] == '#' and ref_path[1] == '$defs':
                    def_name = ref_path[2]
                    if def_name in defs:
                        return _resolve_refs(defs[def_name].copy())
                return obj
            else:
                return {k: _resolve_refs(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [_resolve_refs(item) for item in obj]
        else:
            return obj

    resolved_schema = _resolve_refs(schema)
    if '$defs' in resolved_schema:
        del resolved_schema['$defs']
    return resolved_schema

def _remove_default_field(d: Any):
    """Recursively removes the 'default' key."""
    if isinstance(d, dict):
        if "default" in d:
            del d["default"]
        for value in d.values():
            _remove_default_field(value)
    elif isinstance(d, list):
        for item in d:
            _remove_default_field(item)

def _remove_title_field(d: Any):
    """Recursively removes the 'title' key."""
    if isinstance(d, dict):
        if "title" in d:
            del d["title"]
        for value in d.values():
            _remove_title_field(value)
    elif isinstance(d, list):
        for item in d:
            _remove_title_field(item)

def _remove_anyof_field(d: Any):
    """
    Recursively simplifies 'anyOf' fields by picking the first non-null type.
    """
    if isinstance(d, dict):
        if 'anyOf' in d and isinstance(d['anyOf'], list):
            non_null_schema = next((item for item in d['anyOf' if 'anyOf' in d else 'allOf'] if item.get('type') != 'null'), None)
            if non_null_schema:
                # Delete the anyOf key and update the dict with the first non-null schema
                del d['anyOf' if 'anyOf' in d else 'allOf']
                d.update(non_null_schema)
        
        for value in d.values():
            _remove_anyof_field(value)

    elif isinstance(d, list):
        for item in d:
            _remove_anyof_field(item)

def _map_json_type_to_pydantic(prop_schema: Dict[str, Any]) -> Any:
    """Maps a JSON schema type to a Pydantic type."""
    json_type = prop_schema.get("type")
    if json_type == "string":
        return str
    elif json_type == "integer":
        return int
    elif json_type == "number":
        return float
    elif json_type == "boolean":
        return bool
    elif json_type == "array":
        items_schema = prop_schema.get("items", {})
        item_type = _map_json_type_to_pydantic(items_schema)
        return List[item_type]
    elif json_type == "object":
        return Dict[str, Any]
    return str

def create_dynamic_turn_plan_model(tool_schemas: List[Dict[str, Any]]) -> Type[BaseModel]:
    """
    Dynamically creates a Pydantic model for the turn plan based on available tools.
    """
    fields = {
        "thought": (str, Field(..., description="The model's reasoning for its chosen actions."))
    }

    for schema in tool_schemas:
        tool_name = schema.get("name")
        if not tool_name:
            continue

        sanitized_name = tool_name.replace('.', '_')
        
        arg_fields = {}
        if "parameters" in schema and "properties" in schema["parameters"]:
            for prop_name, prop_schema in schema["parameters"]["properties"].items():
                pydantic_type = _map_json_type_to_pydantic(prop_schema)
                arg_fields[prop_name] = (pydantic_type, Field(..., description=prop_schema.get("description")))
        
        ArgsModel = create_model(f"{sanitized_name}Args", **arg_fields)
        
        fields[sanitized_name] = (Optional[ArgsModel], Field(description=schema.get("description")))

    DynamicTurnPlan = create_model("DynamicTurnPlan", **fields)
    return DynamicTurnPlan
