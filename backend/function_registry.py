import inspect
from typing import Dict, Any, List

class FunctionRegistry:
    def __init__(self):
        self.functions: Dict[str, Dict[str, Any]] = {}

    def register(self, func: callable) -> callable:
        """Register a function for function calling"""
        self.functions[func.__name__] = {
            "function": func,
            "description": func.__doc__.strip() if func.__doc__ else "",
            "parameters": self._extract_parameters(func)
        }
        return func

    def _extract_parameters(self, func: callable) -> Dict[str, Any]:
        """Extract JSON Schema for function parameters"""
        signature = inspect.signature(func)
        properties = {}
        required = []

        for name, param in signature.parameters.items():
            if name == 'self':
                continue

            param_type = "string"  # Default fallback
            if param.annotation == str:
                param_type = "string"
            elif param.annotation == int:
                param_type = "integer"
            elif param.annotation == float:
                param_type = "number"
            elif param.annotation == bool:
                param_type = "boolean"
            elif param.annotation == list:
                param_type = "array"
            elif param.annotation == dict:
                param_type = "object"

            param_schema = {"type": param_type}
            if param.default != inspect.Parameter.empty:
                param_schema["default"] = param.default
            else:
                required.append(name)

            properties[name] = param_schema

        return {
            "type": "object",
            "properties": properties,
            "required": required
        }

    def get_function_call_schema(self) -> List[Dict[str, Any]]:
        """Generate function calling schema for Bedrock-compatible format"""
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": info["description"],
                    "parameters": info["parameters"]
                }
            }
            for name, info in self.functions.items()
        ]

    def call_function(self, function_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a registered function with given arguments"""
        if function_name not in self.functions:
            raise ValueError(f"Function {function_name} not registered")
        func = self.functions[function_name]["function"]
        return func(**arguments)

function_registry = FunctionRegistry()

@function_registry.register
def get_student_info(student_id: str) -> str:
    """Retrieve student information based on student ID"""
    return f"Student Info for ID {student_id}: Name - John Doe, Program - B.Tech CSE, Year - 2nd"