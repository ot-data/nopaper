import inspect
import re
from typing import Dict, Any, List, Optional, Tuple, Set, Callable

class FunctionRegistry:
    def __init__(self):
        self.functions: Dict[str, Dict[str, Any]] = {}
        self.special_queries: Dict[str, Dict[str, Any]] = {}
        self.special_patterns: Dict[str, List[re.Pattern]] = {}

    def register_special_queries(self, function_name: str, queries: List[str]) -> None:
        """Register special queries that should be handled by a specific function"""
        if function_name not in self.functions:
            raise ValueError(f"Function {function_name} not registered")

        # Normalize the queries
        normalized_queries = {self._normalize_query(q) for q in queries}

        # Store the normalized queries
        self.special_queries[function_name] = normalized_queries
        print(f"Registered {len(normalized_queries)} special queries for function: {function_name}")

    def register_special_patterns(self, function_name: str, patterns: List[str]) -> None:
        """Register regex patterns for special queries that should be handled by a specific function"""
        if function_name not in self.functions:
            raise ValueError(f"Function {function_name} not registered")

        # Compile the patterns
        compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]

        # Store the compiled patterns
        self.special_patterns[function_name] = compiled_patterns
        print(f"Registered {len(compiled_patterns)} special patterns for function: {function_name}")

    def _normalize_query(self, query: str) -> str:
        """Normalize query for comparison"""
        query = re.sub(r'[^\w\s]', '', query)
        return ' '.join(query.strip().lower().split())

    def find_special_query_handler(self, query: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Find a function that handles the given special query"""
        normalized = self._normalize_query(query)

        # First try exact matching
        for func_name, queries in self.special_queries.items():
            if normalized in queries:
                return func_name, {"query": query}

        # If no exact match, try pattern matching
        for func_name, patterns in self.special_patterns.items():
            for pattern in patterns:
                if pattern.search(query.lower()):
                    return func_name, {"query": query}

        return None

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

    async def call_function_async(self, function_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a registered function with given arguments asynchronously"""
        if function_name not in self.functions:
            raise ValueError(f"Function {function_name} not registered")

        func = self.functions[function_name]["function"]

        # Check if the function is a coroutine function (async)
        if inspect.iscoroutinefunction(func):
            # For async functions
            result = await func(**arguments)
            return result
        else:
            # For regular functions
            result = func(**arguments)
            return result

function_registry = FunctionRegistry()

@function_registry.register
def get_student_info(student_id: str) -> str:
    """Retrieve student information based on student ID"""
    return f"Student Info for ID {student_id}: Name - John Doe, Program - B.Tech CSE, Year - 2nd"