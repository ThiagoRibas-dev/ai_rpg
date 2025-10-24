import importlib
import pkgutil
from pathlib import Path
from typing import Dict, Any, Callable, List

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
            
            # A tool is defined by a 'schema' and a 'handler' function.
            if hasattr(module, "schema") and hasattr(module, "handler"):
                tool_name = module.schema.get("name")
                if tool_name:
                    self.tools[tool_name] = module.handler
                    self.tool_schemas.append(module.schema)
                    print(f"Registered tool: {tool_name}")

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """Returns the JSON schemas of all registered tools."""
        return self.tool_schemas

    def execute_tool(self, name: str, args: Dict[str, Any]) -> Any:
        """
        Executes a tool by its name with the given arguments.
        
        Args:
            name: The name of the tool to execute.
            args: A dictionary of arguments to pass to the tool's handler.
            
        Returns:
            The result of the tool's execution.
            
        Raises:
            ValueError: If the tool is not found.
        """
        if name not in self.tools:
            raise ValueError(f"Tool '{name}' not found.")
        
        handler = self.tools[name]
        return handler(**args)
