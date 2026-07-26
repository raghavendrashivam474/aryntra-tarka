"""
agent/tools/calculator.py
Safe arithmetic calculator tool.

Uses Python AST parsing instead of eval() to safely
evaluate mathematical expressions.
"""

import ast
import operator
from typing import Any

from backend.utils.logger import get_logger
from backend.agent.tools.base import BaseTool, ToolError

logger = get_logger(__name__)

# Permitted operators only — nothing else allowed
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


def _safe_eval(node: ast.AST) -> float:
    """
    Recursively evaluate an AST node using only permitted operators.

    Args:
        node: AST node to evaluate.

    Returns:
        Numeric result as float.

    Raises:
        ToolError: If an unsupported operation is encountered.
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

    raise ToolError(f"Unsupported expression node: {type(node).__name__}")


class CalculatorTool(BaseTool):
    """
    Arithmetic calculator tool.

    Evaluates mathematical expressions safely.
    Supports: + - * / // % ** and parentheses.
    """

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return (
            "Evaluates arithmetic expressions. "
            "Supports +, -, *, /, //, %, ** and parentheses."
        )

    def execute(self, expression: str = "", **kwargs: Any) -> str:
        """
        Evaluate an arithmetic expression.

        Args:
            expression: Mathematical expression string, e.g. "25 * 18".

        Returns:
            Result as a formatted string.

        Raises:
            ToolError: If expression is missing or cannot be evaluated.
        """
        if not expression:
            raise ToolError("No expression provided to calculator.")

        logger.debug("CalculatorTool evaluating: %s", expression)

        # Normalise common alternate symbols
        cleaned = (
            expression.strip()
            .replace("^", "**")
            .replace("×", "*")
            .replace("÷", "/")
        )

        try:
            tree   = ast.parse(cleaned, mode="eval")
            result = _safe_eval(tree.body)
        except (SyntaxError, ValueError, ZeroDivisionError) as exc:
            raise ToolError(f"Calculation failed: {exc}") from exc

        formatted = int(result) if result == int(result) else result
        logger.info("CalculatorTool: %s = %s", expression, formatted)
        return f"{expression} = {formatted}"
