"""
agent/tools/calculator.py
Safe arithmetic calculator tool.

Sprint 3.15: Added sqrt() function support and ^ operator alias.
Uses Python AST parsing instead of eval() for safety.
"""

import ast
import math
import operator
import re
from typing import Any

from backend.utils.logger import get_logger
from backend.agent.tools.base import BaseTool, ToolError

logger = get_logger(__name__)

# Permitted binary operators
_OPERATORS: dict = {
    ast.Add:      operator.add,
    ast.Sub:      operator.sub,
    ast.Mult:     operator.mul,
    ast.Div:      operator.truediv,
    ast.Pow:      operator.pow,
    ast.USub:     operator.neg,
    ast.UAdd:     operator.pos,
    ast.Mod:      operator.mod,
    ast.FloorDiv: operator.floordiv,
}

# Permitted function calls
_FUNCTIONS: dict = {
    "sqrt": math.sqrt,
    "abs":  abs,
    "round": round,
    "floor": math.floor,
    "ceil":  math.ceil,
}


def _safe_eval(node: ast.AST) -> float:
    """
    Recursively evaluate an AST node using only permitted operators
    and functions.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _OPERATORS:
            raise ToolError(f"Unsupported operator: {op_type.__name__}")
        left  = _safe_eval(node.left)
        right = _safe_eval(node.right)
        return _OPERATORS[op_type](left, right)

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _OPERATORS:
            raise ToolError(f"Unsupported unary operator: {op_type.__name__}")
        return _OPERATORS[op_type](_safe_eval(node.operand))

    # Sprint 3.15: support sqrt(), abs(), round(), floor(), ceil()
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ToolError("Only named functions are permitted.")
        func_name = node.func.id.lower()
        if func_name not in _FUNCTIONS:
            raise ToolError(
                f"Function '{func_name}' is not permitted. "
                f"Allowed: {', '.join(_FUNCTIONS)}"
            )
        args = [_safe_eval(a) for a in node.args]
        return _FUNCTIONS[func_name](*args)

    raise ToolError(f"Unsupported expression node: {type(node).__name__}")


def _preprocess(expression: str) -> str:
    """
    Normalise an expression before AST parsing.

    Conversions:
      ^   -> **        (from normalizer output)
      x   -> *         (unicode multiply)
      ÷   -> /         (unicode divide)
    """
    result = (
        expression.strip()
        .replace("^", "**")
        .replace("\u00d7", "*")
        .replace("\u00f7", "/")
    )
    # Collapse multiple spaces
    result = re.sub(r"\s+", " ", result)
    return result


class CalculatorTool(BaseTool):
    """
    Arithmetic calculator tool.

    Sprint 3.15: supports sqrt(), abs(), round(), floor(), ceil()
    in addition to all standard arithmetic operators.
    """

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return (
            "Evaluates arithmetic expressions. "
            "Supports +, -, *, /, //, %, **, ^, sqrt(), abs(), "
            "round(), floor(), ceil() and parentheses."
        )

    def execute(self, expression: str = "", **kwargs: Any) -> str:
        """
        Evaluate an arithmetic expression.

        Args:
            expression: Mathematical expression string.

        Returns:
            Result as a formatted string: "<expression> = <result>"

        Raises:
            ToolError: If expression is missing or cannot be evaluated.
        """
        if not expression:
            raise ToolError("No expression provided to calculator.")

        logger.debug("[Calculator] Raw expression: %s", expression)

        cleaned = _preprocess(expression)
        logger.debug("[Calculator] Cleaned expression: %s", cleaned)

        try:
            tree   = ast.parse(cleaned, mode="eval")
            result = _safe_eval(tree.body)
        except ToolError:
            raise
        except SyntaxError as exc:
            raise ToolError(
                f"Invalid expression syntax: '{expression}'. "
                f"Error: {exc}"
            ) from exc
        except ZeroDivisionError:
            raise ToolError("Division by zero is undefined.")
        except Exception as exc:
            raise ToolError(f"Calculation failed: {exc}") from exc

        # Format result — integer if whole number, float otherwise
        if isinstance(result, float) and result.is_integer():
            formatted = int(result)
        else:
            formatted = round(result, 10)

        logger.info("[Calculator] %s = %s", expression, formatted)
        return f"{expression} = {formatted}"
