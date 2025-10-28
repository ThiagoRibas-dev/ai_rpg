import importlib
import pkgutil
from pathlib import Path
from typing import Dict, Any, Callable, List, Type
from pydantic import BaseModel
from app.tools import schemas as tool_schemas

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


_TOOL_SCHEMA_MAP: Dict[str, Type[BaseModel]] = {
    "math.eval": tool_schemas.MathEval,
    "memory.upsert": tool_schemas.MemoryUpsert,
    "rag.search": tool_schemas.RagSearch,
    "rng.roll": tool_schemas.RngRoll,
    "rules.resolve_action": tool_schemas.RulesResolveAction,
    "state.apply_patch": tool_schemas.StateApplyPatch,
    "state.query": tool_schemas.StateQuery,
    "time.now": tool_schemas.TimeNow,
}

class ToolRegistry:
    """
    Discovers, loads, and executes tools from the 'tools.builtin' package.
    """
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.tool_schemas: List[Dict[str, Any]] = []
        self._discover_tools()

    def _discover_tools(self):
        """
        Dynamically imports all modules in the 'app.tools.builtin' package
        and registers the tools they contain.
        """
        import app.tools.builtin as builtin_tools
        
        package_path = Path(builtin_tools.__file__).parent
        
        for _, module_name, _ in pkgutil.iter_modules([str(package_path)]):
            module = importlib.import_module(f"app.tools.builtin.{module_name}")
            
            if hasattr(module, "schema") and hasattr(module, "handler"):
                tool_name = module.schema.get("name")
                if tool_name and tool_name in _TOOL_SCHEMA_MAP:
                    self.tools[tool_name] = module.handler
                    pydantic_model = _TOOL_SCHEMA_MAP[tool_name]
                    schema = pydantic_model.model_json_schema()
                    description = pydantic_model.__doc__
                    
                    properties = schema.get("properties", {})
                    if "name" in properties:
                        del properties["name"]

                    for prop_schema in properties.values():
                        if "title" in prop_schema:
                            del prop_schema["title"]
                    
                    _remove_default_field(properties)
                        
                    required = schema.get("required", [])
                    if "name" in required:
                        required.remove("name")

                    parameters_schema = {
                        "properties": properties,
                        "required": required,
                    }
                    if not properties:
                        del parameters_schema["properties"]
                    if not required:
                        del parameters_schema["required"]

                    transformed_schema = {
                        "name": tool_name,
                        "description": description,
                        "parameters": parameters_schema,
                    }
                    self.tool_schemas.append(transformed_schema)
                    print(f"Registered tool: {tool_name}")

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """Returns the JSON schemas of all registered tools."""
        return self.tool_schemas

    def execute_tool(self, name: str, args: Dict[str, Any]) -> Any:
        """
        Executes a tool by name with the given arguments.
        """
        if name not in self.tools:
            raise ValueError(f"Tool '{name}' not found.")

        pydantic_schema = _TOOL_SCHEMA_MAP.get(name)
        if not pydantic_schema:
            raise ValueError(f"Schema for tool '{name}' not found.")

        try:
            tool_model = pydantic_schema(**args)
        except Exception as e:
            raise ValueError(f"Invalid arguments for tool '{name}': {e}")

        handler = self.tools[name]
        handler_args = tool_model.model_dump()
        handler_args.pop("name", None)
        return handler(**handler_args)
