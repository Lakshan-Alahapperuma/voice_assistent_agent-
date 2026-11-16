from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import inspect
import json

class BaseTool(ABC):
    """Abstract base class for all Nova tools."""

    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = {}
    requires_confirmation: bool = False

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """Executes the tool with the given arguments."""
        pass

    def to_ollama_tool(self) -> Dict[str, Any]:
        """Converts the tool definition into Ollama / OpenAI function format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters or {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }

class ToolRegistry:
    """Registry managing available tools and dispatching execution."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[BaseTool]:
        return list(self._tools.values())

    def get_ollama_tools(self) -> List[Dict[str, Any]]:
        return [tool.to_ollama_tool() for tool in self._tools.values()]

    def execute(self, name: str, arguments: Dict[str, Any]) -> Any:
        tool = self.get_tool(name)
        if not tool:
            return {"error": f"Tool '{name}' is not registered."}
        try:
            return tool.execute(**arguments)
        except Exception as e:
            return {"error": f"Failed to execute '{name}': {str(e)}"}
