import importlib
import logging
import pkgutil
from pathlib import Path
import copy
from typing import Any, Callable, Dict, List, Type

from pydantic import BaseModel

from app.tools import schemas as tool_schemas

logger = logging.getLogger(__name__)


def _clean_schema(d: Any):
    """Recursively cleans schema for LLM compatibility."""
    if isinstance(d, dict):
        keys_to_remove = [
            "default",
            "title",
            "additionalProperties",
            "additional_properties",
        ]
        for key in keys_to_remove:
            if key in d:
                del d[key]
        for value in d.values():
            _clean_schema(value)
    elif isinstance(d, list):
        for item in d:
            _clean_schema(item)


def _resolve_refs(schema_part: Any, defs: Dict[str, Any]) -> Any:
    """Recursively resolves $ref in schema."""
    if isinstance(schema_part, dict):
        if "$ref" in schema_part:
            ref_path = schema_part["$ref"]
            if ref_path.startswith("#/$defs/") or ref_path.startswith("#/definitions/"):
                def_name = ref_path.split("/")[-1]
                if def_name in defs:
                    return _resolve_refs(copy.deepcopy(defs[def_name]), defs)
            return schema_part
        return {k: _resolve_refs(v, defs) for k, v in schema_part.items()}
    elif isinstance(schema_part, list):
        return [_resolve_refs(item, defs) for item in schema_part]
    return schema_part


class ToolRegistry:
    """
    Discovers, loads, and executes tools.
    Updated to scan 'app.tools.handlers'.
    """

    def __init__(self):
        self._handlers: Dict[Type[BaseModel], Callable] = {}
        self.tool_schemas: List[Dict[str, Any]] = []
        self._discover_tools()

    def _discover_tools(self):
        """
        Auto-discovers tools in app.tools.handlers (Atomic) AND app.tools.builtin (Legacy/Setup).
        """
        import app.tools.handlers as atomic_tools
        import app.tools.builtin as builtin_tools

        # 1. Map Tool Names -> Pydantic Types
        name_to_type: Dict[str, Type[BaseModel]] = {}
        for attr_name in dir(tool_schemas):
            attr = getattr(tool_schemas, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, BaseModel)
                and attr is not BaseModel
                and hasattr(attr, "model_fields")
                and "name" in attr.model_fields
            ):
                tool_name = attr.model_fields["name"].default
                name_to_type[tool_name] = attr

        logger.debug(f"Found {len(name_to_type)} tool schemas")

        # 2. Discover Handlers in both packages
        # We prefer handlers in 'atomic_tools' if duplicates exist

        search_packages = [
            (atomic_tools, "app.tools.handlers"),
            (builtin_tools, "app.tools.builtin"),
        ]

        for pkg, pkg_name in search_packages:
            path = Path(pkg.__file__).parent

            for _, module_name, _ in pkgutil.iter_modules([str(path)]):
                if module_name.startswith("_"):
                    continue

                try:
                    module = importlib.import_module(f"{pkg_name}.{module_name}")

                    if not hasattr(module, "handler"):
                        continue

                    # Map module "adjust" -> tool "adjust"
                    # Map module "npc_spawn" -> tool "npc.spawn"

                    # Try direct match first
                    schema_type = None

                    # Strategy A: Module name matches tool name exactly (e.g. adjust)
                    if module_name in name_to_type:
                        schema_type = name_to_type[module_name]

                    # Strategy B: Module name with dot replaced by underscore (e.g. npc_spawn -> npc.spawn)
                    if not schema_type:
                        potential_name = module_name.replace("_", ".")
                        if potential_name in name_to_type:
                            schema_type = name_to_type[potential_name]

                    if not schema_type:
                        # logger.debug(f"Skipping {module_name}: no matching schema found.")
                        continue

                    # Register if not already registered (first come, first served)
                    if schema_type not in self._handlers:
                        self._handlers[schema_type] = module.handler
                        self._register_schema(schema_type)
                        logger.info(
                            f"Registered tool: {schema_type.model_fields['name'].default} from {module_name}"
                        )

                except Exception as e:
                    logger.error(f"Failed to load {module_name}: {e}", exc_info=True)

    def _register_schema(self, schema_type: Type[BaseModel]):
        schema = schema_type.model_json_schema()
        defs = schema.get("$defs", {}) or schema.get("definitions", {})
        properties = schema.get("properties", {}).copy()
        properties.pop("name", None)
        properties = _resolve_refs(properties, defs)
        _clean_schema(properties)

        # Ensure all parameters have a JSON Schema "type" where possible.
        # Some fields (like 'Any') produce schemas with only a description/title,
        # which llama.cpp's JSON-schema-to-BNF converter does not accept.
        for prop_name, prop_schema in properties.items():
            if not isinstance(prop_schema, dict):
                continue
            # Skip schemas that already declare a type or use combinators/refs/enums
            if "type" in prop_schema:
                continue
            if any(
                key in prop_schema
                for key in ("oneOf", "anyOf", "allOf", "enum", "$ref")
            ):
                continue
            # Fallback: treat as string for schema purposes
            prop_schema["type"] = "string"

        required = [r for r in schema.get("required", []) if r != "name"]

        parameters_schema = {"type": "object"}
        if properties:
            parameters_schema["properties"] = properties
        if required:
            parameters_schema["required"] = required

        self.tool_schemas.append(
            {
                "name": schema_type.model_fields["name"].default,
                "description": schema_type.__doc__ or "",
                "parameters": parameters_schema,
            }
        )

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        return self.tool_schemas

    def get_all_tool_types(self) -> List[Type[BaseModel]]:
        return list(self._handlers.keys())

    def get_llm_tool_schemas(self, tool_names: List[str]) -> List[Dict[str, Any]]:
        llm_schemas = []
        for schema in self.tool_schemas:
            if schema["name"] in tool_names:
                llm_schemas.append(
                    {
                        "type": "function",
                        "function": {
                            "name": schema["name"],
                            "description": schema["description"],
                            "parameters": schema["parameters"],
                        },
                    }
                )
        return llm_schemas

    def execute(
        self, tool_model: BaseModel, context: Dict[str, Any] | None = None
    ) -> Any:
        tool_type = type(tool_model)
        if tool_type not in self._handlers:
            raise ValueError(f"Unknown tool type: {tool_type.__name__}")

        handler = self._handlers[tool_type]
        args = tool_model.model_dump(exclude={"name"})
        if context:
            args.update(context)

        return handler(**args)
