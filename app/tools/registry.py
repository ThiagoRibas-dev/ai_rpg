import importlib
import logging
import pkgutil
from pathlib import Path
from typing import Any, Callable, Dict, List, Type

from pydantic import BaseModel

from app.tools import schemas as tool_schemas

logger = logging.getLogger(__name__)


def _clean_schema(d: Any):
    """
    Recursively cleans the schema for Gemini compatibility.
    Removes keys that are not supported or cause issues in the Gemini API.
    """
    if isinstance(d, dict):
        # Keys to remove
        # 'additionalProperties' is not supported by Gemini function calling.
        # 'default' and 'title' are also often problematic or unnecessary.
        keys_to_remove = [
            "default",
            "title",
            "additionalProperties",
            "additional_properties",
        ]
        for key in keys_to_remove:
            if key in d:
                del d[key]

        # Recurse into values
        for value in d.values():
            _clean_schema(value)

    elif isinstance(d, list):
        for item in d:
            _clean_schema(item)


class ToolRegistry:
    """
    Discovers, loads, and executes tools from the 'tools.builtin' package.
    Uses type-based lookup for clean, type-safe execution.
    """

    def __init__(self):
        self._handlers: Dict[Type[BaseModel], Callable] = {}
        self.tool_schemas: List[Dict[str, Any]] = []
        self._discover_tools()

    def _discover_tools(self):
        """
        Automatically discovers and registers tools using name-based matching.

        NEW APPROACH:
        - Scan app.tools.builtin for Python files with handler() functions
        - Match module names to Pydantic schema types by tool name
        - No more redundant schema dicts needed!
        """
        import app.tools.builtin as builtin_tools

        package_path = Path(builtin_tools.__file__).parent

        # Build a map of tool names -> Pydantic types by inspecting the schemas module
        name_to_type: Dict[str, Type[BaseModel]] = {}

        for attr_name in dir(tool_schemas):
            attr = getattr(tool_schemas, attr_name)

            # Check if it's a Pydantic model class with a 'name' field
            if (
                isinstance(attr, type)
                and issubclass(attr, BaseModel)
                and attr is not BaseModel
                and hasattr(attr, "model_fields")
                and "name" in attr.model_fields
            ):
                # Extract the tool name from the Literal field
                tool_name = attr.model_fields["name"].default
                name_to_type[tool_name] = attr

        logger.debug(f"Found {len(name_to_type)} Pydantic tool schemas")

        # Build reverse map: expected module name -> tool name
        # e.g., "memory.upsert" -> "memory_upsert"
        module_name_to_tool_name: Dict[str, str] = {}
        for tool_name in name_to_type.keys():
            # Convert "memory.upsert" -> "memory_upsert"
            expected_module = tool_name.replace(".", "_")
            module_name_to_tool_name[expected_module] = tool_name

        # Auto-discover handler modules
        for _, module_name, _ in pkgutil.iter_modules([str(package_path)]):
            if module_name.startswith("_"):
                continue  # Skip private modules

            try:
                module = importlib.import_module(f"app.tools.builtin.{module_name}")

                # Check if module has a handler function
                if not hasattr(module, "handler"):
                    logger.debug(f"Skipping {module_name}: no handler() function")
                    continue

                # Match module name to tool name
                if module_name not in module_name_to_tool_name:
                    logger.warning(
                        f"Module {module_name} has no matching Pydantic schema (expected tool name: {module_name.replace('_', '.')})"
                    )
                    continue

                tool_name = module_name_to_tool_name[module_name]
                schema_type = name_to_type[tool_name]

                # Register: Type -> Handler
                self._handlers[schema_type] = module.handler

                # Generate JSON schema for LLM
                self._register_schema(schema_type)

                logger.info(
                    f"Registered tool: {tool_name} ({schema_type.__name__} <- {module_name}.py)"
                )

            except Exception as e:
                logger.error(
                    f"Failed to load tool module {module_name}: {e}", exc_info=True
                )

    def _register_schema(self, schema_type: Type[BaseModel]):
        """Generate JSON schema from Pydantic type for LLM consumption."""
        schema = schema_type.model_json_schema()
        description = schema_type.__doc__ or "No description available"

        # Extract properties, excluding the discriminator field 'name'
        properties = schema.get("properties", {}).copy()
        properties.pop("name", None)

        # Clean up schema for LLM (remove titles, defaults, additionalProperties)
        _clean_schema(properties)

        # Extract required fields, excluding 'name'
        required = [r for r in schema.get("required", []) if r != "name"]

        # Build parameters schema
        parameters_schema = {"type": "object"}
        if properties:
            parameters_schema["properties"] = properties
        if required:
            parameters_schema["required"] = required

        # Store complete tool schema
        self.tool_schemas.append(
            {
                "name": self._get_tool_name(schema_type),
                "description": description,
                "parameters": parameters_schema,
            }
        )

    @staticmethod
    def _get_tool_name(schema_type: Type[BaseModel]) -> str:
        """Extract tool name from Pydantic type."""
        return schema_type.model_fields["name"].default

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """Returns the JSON schemas of all registered tools for LLM."""
        return self.tool_schemas

    def get_all_tool_names(self) -> List[str]:
        """Get all registered tool names."""
        return [self._get_tool_name(t) for t in self._handlers.keys()]

    def get_all_tool_types(self) -> List[Type[BaseModel]]:
        """Get all registered Pydantic tool types."""
        return list(self._handlers.keys())

    def get_tool_models(self, tool_names: List[str]) -> List[Type[BaseModel]]:
        """
        Returns the Pydantic model types for a given list of tool names.
        Used when creating discriminated unions for specific contexts (e.g., SETUP vs GAMEPLAY).
        """
        name_to_type = {self._get_tool_name(t): t for t in self._handlers.keys()}
        return [name_to_type[name] for name in tool_names if name in name_to_type]

    def get_llm_tool_schemas(self, tool_names: List[str]) -> List[Dict[str, Any]]:
        """
        Returns the JSON schemas for a given list of tools, formatted for LLM tool-calling APIs.
        This renames 'tool_name' to 'name' for API compatibility.
        """
        llm_schemas = []
        for schema in self.tool_schemas:
            if schema["name"] in tool_names:
                # Create the format expected by OpenAI/Gemini tool calling
                formatted_schema = {
                    "type": "function",
                    "function": {
                        "name": schema["name"],
                        "description": schema["description"],
                        "parameters": schema["parameters"],
                    },
                }
                llm_schemas.append(formatted_schema)
        return llm_schemas

    def execute(
        self, tool_model: BaseModel, context: Dict[str, Any] | None = None
    ) -> Any:
        """
        Execute a tool using an already-validated Pydantic model instance.

        Args:
            tool_model: A validated Pydantic instance (e.g., MathEval, MemoryUpsert)
            context: Optional context dict (session_id, db_manager, vector_store, etc.)

        Returns:
            The result from the tool handler
        """
        tool_type = type(tool_model)

        if tool_type not in self._handlers:
            raise ValueError(f"Unknown tool type: {tool_type.__name__}")

        handler = self._handlers[tool_type]

        # Extract all fields except the discriminator 'tool_name'
        handler_args = tool_model.model_dump(exclude={"name"})

        # Merge in context
        if context:
            handler_args.update(context)

        tool_name = self._get_tool_name(tool_type)
        logger.debug(f"Executing {tool_name} with args: {list(handler_args.keys())}")

        return handler(**handler_args)
