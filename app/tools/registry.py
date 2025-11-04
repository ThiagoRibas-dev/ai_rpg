import importlib
import pkgutil
from pathlib import Path
import logging
from typing import Dict, Any, Callable, List, Type
from pydantic import BaseModel
from app.tools import schemas as tool_schemas

logger = logging.getLogger(__name__)


def _remove_default_field(d: Any):
    """Recursively traverses a dictionary or list and removes the 'default' key."""
    if isinstance(d, dict):
        if "default" in d:
            del d["default"]
        for value in d.values():
            _remove_default_field(value)
    elif isinstance(d, list):
        for item in d:
            _remove_default_field(item)


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
        """Automatically discovers and registers tools. No hardcoded mappings needed!"""
        import app.tools.builtin as builtin_tools
        
        package_path = Path(builtin_tools.__file__).parent
        
        # Build a map of tool names → Pydantic types by inspecting the schemas module
        name_to_type: Dict[str, Type[BaseModel]] = {}
        
        for attr_name in dir(tool_schemas):
            attr = getattr(tool_schemas, attr_name)
            
            # Check if it's a Pydantic model class with a 'name' field
            if (isinstance(attr, type) and 
                issubclass(attr, BaseModel) and 
                attr is not BaseModel and
                hasattr(attr, "model_fields") and
                "name" in attr.model_fields):
                
                # Extract the tool name from the Literal field
                tool_name = attr.model_fields["name"].default
                name_to_type[tool_name] = attr
        
        logger.debug(f"Found {len(name_to_type)} Pydantic tool schemas")
        
        # Auto-discover handler modules and match them to Pydantic types
        for _, module_name, _ in pkgutil.iter_modules([str(package_path)]):
            if module_name.startswith("_"):
                continue  # Skip private modules
            
            try:
                module = importlib.import_module(f"app.tools.builtin.{module_name}")
                
                if not (hasattr(module, "schema") and hasattr(module, "handler")):
                    continue
                
                # Get the tool name from the module's schema dict
                tool_name = module.schema.get("name")
                if not tool_name:
                    logger.warning(f"Module {module_name} has no 'name' in schema")
                    continue
                
                # Match to Pydantic type by name
                if tool_name not in name_to_type:
                    logger.warning(f"No Pydantic schema found for tool '{tool_name}' (module: {module_name})")
                    continue
                
                schema_type = name_to_type[tool_name]
                
                # Register: Type → Handler
                self._handlers[schema_type] = module.handler
                
                # Generate JSON schema for LLM
                self._register_schema(schema_type)
                
                logger.info(f"Registered tool: {tool_name} ({schema_type.__name__} ← {module_name}.py)")
                
            except Exception as e:
                logger.error(f"Failed to load tool module {module_name}: {e}", exc_info=True)

    def _register_schema(self, schema_type: Type[BaseModel]):
        """Generate JSON schema from Pydantic type for LLM consumption."""
        schema = schema_type.model_json_schema()
        description = schema_type.__doc__ or "No description available"
        
        # Extract properties, excluding the discriminator field 'name'
        properties = schema.get("properties", {}).copy()
        properties.pop("name", None)
        
        # Clean up schema for LLM (remove titles, defaults)
        for prop_schema in properties.values():
            prop_schema.pop("title", None)
        _remove_default_field(properties)
        
        # Extract required fields, excluding 'name'
        required = [r for r in schema.get("required", []) if r != "name"]
        
        # Build parameters schema
        parameters_schema = {"type": "object"}
        if properties:
            parameters_schema["properties"] = properties
        if required:
            parameters_schema["required"] = required
        
        # Store complete tool schema
        self.tool_schemas.append({
            "name": self._get_tool_name(schema_type),
            "description": description,
            "parameters": parameters_schema,
        })

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

    def execute(self, tool_model: BaseModel, context: Dict[str, Any] | None = None) -> Any:
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
        
        # Extract all fields except the discriminator 'name'
        handler_args = tool_model.model_dump(exclude={"name"})
        
        # Merge in context
        if context:
            handler_args.update(context)
        
        tool_name = self._get_tool_name(tool_type)
        logger.debug(f"Executing {tool_name} with args: {list(handler_args.keys())}")
        
        return handler(**handler_args)