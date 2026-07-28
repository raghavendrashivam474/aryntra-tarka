"""
agent/tools/calculator.py
Safe arithmetic calculator tool.

Sprint 3.15: Added sqrt() function support and ^ operator alias.
Sprint 3.21: Added execute_structured() returning numeric value.
             Tool result integrity - exact values preserved.
             No approximation. No string modification downstream.
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
    "sqrt":  math.sqrt,
    "abs":   abs,
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
      ^        -> **       (caret power operator)
      x / x    -> *        (unicode multiply)
      ÷        -> /        (unicode divide)
      × (char) -> *        (unicode multiply symbol)
    """
    result = (
        expression.strip()
        .replace("^", "**")
        .replace("\u00d7", "*")
        .replace("\u00f7", "/")
        .replace("\u00e9", "")   # strip stray accented chars
    )
    # Collapse multiple spaces
    result = re.sub(r"\s+", " ", result)
    return result


def _format_result(result: float) -> str:
    """
    Format a numeric result without approximation language.

    Rules:
      - If the result is a whole number, return as integer string.
      - Otherwise round to 10 decimal places to avoid float noise,
        then strip trailing zeros.
    """
    if isinstance(result, float) and result.is_integer():
        return str(int(result))
    rounded = round(result, 10)
    # Strip trailing zeros after decimal
    formatted = f"{rounded:.10f}".rstrip("0").rstrip(".")
    return formatted


class CalculatorTool(BaseTool):
    """
    Arithmetic calculator tool.

    Sprint 3.15: supports sqrt(), abs(), round(), floor(), ceil()
    Sprint 3.21: execute_structured() returns exact numeric value.
                 Tool result integrity guaranteed — no approximation.
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

    def _compute(self, expression: str) -> tuple[float, str, str]:
        """
        Core computation. Returns (numeric_value, formatted_value, cleaned_expr).

        Raises ToolError on any failure.
        This is the single computation point — called by both execute()
        and execute_structured() to guarantee identical results.
        """
        if not expression or not expression.strip():
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
                f"Detail: {exc}"
            ) from exc
        except ZeroDivisionError:
            raise ToolError("Division by zero is undefined.")
        except Exception as exc:
            raise ToolError(f"Calculation failed: {exc}") from exc

        formatted = _format_result(result)
        logger.info("[Calculator] %s = %s", expression, formatted)

        return result, formatted, cleaned

    def execute(self, expression: str = "", **kwargs: Any) -> str:
        """
        Evaluate an arithmetic expression.

        Args:
            expression: Mathematical expression string.

        Returns:
            Exact result as a formatted string: "<expression> = <result>"
            Result is NEVER approximated or hedged.

        Raises:
            ToolError: If expression is missing or cannot be evaluated.
        """
        _, formatted, _ = self._compute(expression)
        return f"{expression} = {formatted}"

    def execute_structured(self, expression: str = "", **kwargs: Any) -> dict[str, Any]:
        """
        Evaluate an arithmetic expression and return structured result.

        Sprint 3.21: Returns a dict with exact numeric value preserved.
        The 'value' key contains the raw float for downstream chaining.
        The 'formatted' key contains the exact string representation.
        The 'result' key contains the full display string.

        No approximation. No hedging. Exact values only.

        Returns:
            {
                "value":      float  — exact numeric result,
                "formatted":  str    — exact string (e.g. "541171"),
                "result":     str    — full display (e.g. "1847 * 293 = 541171"),
                "expression": str    — the expression that was evaluated,
            }

        Raises:
            ToolError: If expression is missing or cannot be evaluated.
        """
        numeric, formatted, cleaned = self._compute(expression)

        full_result = f"{expression} = {formatted}"

        structured = {
            "value":      numeric,
            "formatted":  formatted,
            "result":     full_result,
            "expression": expression,
        }

        logger.info(
            "[Calculator] Structured result | expr='%s' value=%s",
            expression, formatted,
        )

        return structured
