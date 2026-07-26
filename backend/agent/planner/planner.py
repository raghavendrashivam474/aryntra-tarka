r"""
agent/planner/planner.py
Rule-based request planner.

Converts a user message into a structured ExecutionPlan.
Rules evaluated in order - first match wins.
Calculator checked BEFORE datetime so "times" routes correctly.

Pattern conventions:
  "word"    -> whole-word match (\bword\b)
  "prefix*" -> prefix match (\bprefix\w*)

Sprint 3.2 — DateTime intent recognition expanded.
  Added: "time", "date", "day", "date and time", "today's time",
         "today's date", "current date", "tell me the time",
         "tell me the date", "what's the time", "what's the date"
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from backend.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ExecutionPlan:
    """Structured plan produced by the Planner."""

    tool_name: str | None
    parameters: dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""


# Map English math words to symbolic operators.
# Longer phrases first so multi-word forms win over single words.
_WORD_TO_OP = [
    ("multiplied by", "*"),
    ("multiply by",   "*"),
    ("divided by",    "/"),
    ("divide by",     "/"),
    ("added to",      "+"),
    ("power of",      "**"),
    ("raised to",     "**"),
    ("to the power",  "**"),
    ("plus",  "+"),
    ("minus", "-"),
    ("times", "*"),
    ("over",  "/"),
    ("modulo", "%"),
    ("mod",    "%"),
]


def _normalise_math_words(text: str) -> str:
    """Convert English math words to symbols. Case-insensitive."""
    result = text.lower()
    for phrase, symbol in _WORD_TO_OP:
        pattern = r"\b" + re.escape(phrase) + r"\b"
        result = re.sub(pattern, f" {symbol} ", result)
    return result


def _extract_expression(message: str) -> dict[str, Any]:
    """
    Extract a mathematical expression from the message.

    Steps:
      1. Replace unicode math symbols with ASCII equivalents.
      2. Convert English math words to symbols.
      3. Extract the longest run of digits, spaces, and operators.
    """
    cleaned = (
        message
        .replace("\u00d7", "*")  # multiplication sign
        .replace("\u00f7", "/")  # division sign
        .replace("^", "**")
    )

    normalised = _normalise_math_words(cleaned)

    # Extract runs of digits and operators (with spaces).
    # Must start and end with a digit or paren.
    pattern = r"[\d(][\d\s()+\-*/%.]*[\d)]"
    matches = re.findall(pattern, normalised)

    if matches:
        expression = max(matches, key=len).strip()
        expression = re.sub(r"\s+", " ", expression)
        return {"expression": expression}

    digits = re.search(r"\d+", normalised)
    if digits:
        return {"expression": digits.group()}

    return {"expression": message}


def _extract_path(message: str) -> dict[str, Any]:
    """Extract a path only if it looks like a real path."""
    path_match = re.search(
        r"(?:in|at|of|inside)\s+([./~\\][\w./\\-]*)",
        message,
    )
    if path_match:
        return {"path": path_match.group(1)}
    return {"path": "."}


def _matches(patterns: list, text: str) -> bool:
    """
    Return True if any pattern matches in text.

    Pattern conventions:
      "word"     -> whole-word match
      "prefix*"  -> word starting with prefix (any suffix)
    """
    for pattern in patterns:
        if pattern.endswith("*"):
            # Prefix match - word starting with prefix
            prefix = re.escape(pattern[:-1])
            regex = r"\b" + prefix + r"\w*"
        else:
            # Whole word or exact phrase match
            regex = r"\b" + re.escape(pattern) + r"\b"

        if re.search(regex, text):
            return True
    return False


# ---------------------------------------------------------------------------
# Routing rules
#
# Calculator MUST come before datetime so "times" does not trigger "time".
#
# DateTime patterns — Sprint 3.2 expansion:
#   Short queries  : "time", "date", "day"
#   Possessives    : "today's date", "today's time"
#   Compound       : "date and time", "current date and time"
#   Conversational : "tell me the time", "what's the time"
#   Existing       : all original patterns retained unchanged
# ---------------------------------------------------------------------------

_RULES = [
    (
        [
            # Prefix patterns: match calculate, calculating, calculation, etc.
            "calculat*",
            "comput*",
            "multipl*",
            "divid*",
            "subtract*",
            "evaluat*",
            # Whole-word patterns
            "math",
            "add",
            "plus",
            "minus",
            "times",
            "solve",
            "result of",
            "how much is",
        ],
        "calculator",
        _extract_expression,
    ),
    (
        [
            # ── Original patterns (unchanged) ───────────────────────────
            "what time",
            "current time",
            "what day",
            "what date",
            "right now",
            "what year",
            "what month",
            "today",
            "clock",
            "time is",
            "date is",
            # ── Sprint 3.2 additions ────────────────────────────────────
            # Single-word short queries
            "time",
            "date",
            "day",
            # Possessive forms
            "today's date",
            "today's time",
            "current date",
            # Compound date-and-time requests
            "date and time",
            "current date and time",
            "today's date and time",
            # Conversational variants
            "tell me the time",
            "tell me the date",
            "tell me the day",
            "what's the time",
            "what's the date",
            "what's today",
            "what is today",
            "what is the time",
            "what is the date",
            "what is the day",
            "can you tell me the time",
            "can you tell me the date",
        ],
        "datetime",
        lambda msg: {},
    ),
    (
        [
            "list files", "list the files", "show files",
            "files in", "what files",
            "directory", "folder",
        ],
        "filesystem",
        _extract_path,
    ),
]


class Planner:
    """Rule-based planner. Decides which tool to use. Never executes."""

    def plan(self, message: str) -> ExecutionPlan:
        """
        Analyse the user message and produce an execution plan.

        Args:
            message: Raw user message string.

        Returns:
            ExecutionPlan with tool selection and parameters.
        """
        normalised = message.lower().strip()
        logger.info("Planner analysing: '%s'", message)

        for patterns, tool_name, extractor in _RULES:
            if _matches(patterns, normalised):
                params = extractor(message)
                plan = ExecutionPlan(
                    tool_name=tool_name,
                    parameters=params,
                    reasoning=f"Keyword match: '{tool_name}' selected.",
                )
                logger.info(
                    "Planner: tool='%s' params=%s",
                    plan.tool_name,
                    plan.parameters,
                )
                return plan

        plan = ExecutionPlan(
            tool_name=None,
            parameters={},
            reasoning="No matching tool. Provider responds directly.",
        )
        logger.info("Planner: no tool selected, direct response")
        return plan
