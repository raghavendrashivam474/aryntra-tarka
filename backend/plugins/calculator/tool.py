from typing import Any, Dict
from runtime.plugins.base import PluginBase


class CalculatorPlugin(PluginBase):

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Performs basic arithmetic: add, subtract, multiply, divide."

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def input_schema(self) -> Dict:
        return {
            "operation": "string (add | subtract | multiply | divide)",
            "a": "number",
            "b": "number"
        }

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        operation = input_data.get("operation")
        a = float(input_data.get("a", 0))
        b = float(input_data.get("b", 0))

        operations = {
            "add":      lambda: a + b,
            "subtract": lambda: a - b,
            "multiply": lambda: a * b,
            "divide":   lambda: a / b if b != 0 else None,
        }

        if operation not in operations:
            return {"error": f"Unknown operation: {operation}"}

        result = operations[operation]()

        if result is None:
            return {"error": "Division by zero."}

        return {
            "operation": operation,
            "a": a,
            "b": b,
            "result": result
        }
