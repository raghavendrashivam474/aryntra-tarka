r"""
agent/planner/planner.py
Rule-based request planner.

Converts a user message into a structured ExecutionPlan.
Rules evaluated in order — ALL matching rules are collected.
Calculator checked BEFORE datetime so "times" routes correctly.

Sprint 3.2 — DateTime intent recognition expanded.
Sprint 3.6 — Multi-tool planning. Planner now collects ALL matching
             rules rather than stopping at the first match.
             ExecutionPlanStep introduced for per-tool parameters.
             ExecutionPlan.steps holds the ordered execution list.
             ExecutionPlan.tool_name / .parameters retained for
             backward compatibility with Sprint 3.2 / 3.5 tests.

Pattern conventions:
  "word"    -> whole-word match (\bword\b)
  "prefix*" -> prefix match (\bprefix\w*)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from backend.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# ExecutionPlanStep — one tool invocation within a plan
# ---------------------------------------------------------------------------

@dataclass
class ExecutionPlanStep:
    """A single tool invocation within an ExecutionPlan."""

    tool_name:  str
    parameters: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# ExecutionPlan — full plan returned by the Planner
# ---------------------------------------------------------------------------

@dataclass
class ExecutionPlan:
    """
    Structured plan produced by the Planner.

    Attributes:
        steps:      Ordered list of tool invocations to execute.
                    Empty when no tool is needed.
        tool_name:  First tool name, or None. Retained for backward
                    compatibility with Sprint 3.2 / 3.5 tests.
        parameters: First tool parameters, or {}. Retained for
                    backward compatibility.
        reasoning:  Human-readable explanation of the planning decision.
    """

    steps:      list[ExecutionPlanStep] = field(default_factory=list)
    tool_name:  str | None              = None
    parameters: dict[str, Any]          = field(default_factory=dict)
    reasoning:  str                     = ""


# ---------------------------------------------------------------------------
# Math word normalisation
# ---------------------------------------------------------------------------

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
            prefix = re.escape(pattern[:-1])
            regex = r"\b" + prefix + r"\w*"
        else:
            regex = r"\b" + re.escape(pattern) + r"\b"

        if re.search(regex, text):
            return True
    return False


# ---------------------------------------------------------------------------
# Routing rules
#
# Calculator MUST come before datetime so "times" does not trigger "time".
#
# Sprint 3.6: ALL matching rules are collected, not just the first.
# Order is preserved — steps are appended in rule-list order.
# ---------------------------------------------------------------------------

_RULES = [
    (
        [
            "calculat*",
            "comput*",
            "multipl*",
            "divid*",
            "subtract*",
            "evaluat*",
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
            "time",
            "date",
            "day",
            "today's date",
            "today's time",
            "current date",
            "date and time",
            "current date and time",
            "today's date and time",
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


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------

class Planner:
    """
    Rule-based planner.

    Sprint 3.6: Collects ALL matching rules to support multi-tool
    execution. Single-tool and no-tool cases are handled identically
    to previous sprints.
    """

    def plan(self, message: str) -> ExecutionPlan:
        """
        Analyse the user message and produce an execution plan.

        All matching rules are evaluated. Steps are added in rule-list
        order, which mirrors the order tools appear in the request.

        Args:
            message: Raw user message string.

        Returns:
            ExecutionPlan with zero, one, or many steps.
        """
        normalised = message.lower().strip()
        logger.info("Planner analysing: '%s'", message)

        steps: list[ExecutionPlanStep] = []

        # Sprint 3.10.1: implicit calculator trigger.
        # If the message contains a digit AND an arithmetic operator
        # (symbol or word), force calculator match. This catches
        # "What is 5 + 5?" which lacks the explicit "calculate" keyword,
        # WITHOUT breaking pure datetime queries like "What's the time?".
        has_digit = bool(re.search(r"\d", normalised))
        has_operator = bool(
            re.search(
                r"[+\-*/%^]|"
                r"\bplus\b|\bminus\b|\btimes\b|\bover\b|"
                r"\bdivided\b|\bmultiplied\b",
                normalised,
            )
        )
        implicit_calc = has_digit and has_operator

        for patterns, tool_name, extractor in _RULES:
            matched = _matches(patterns, normalised)
            if tool_name == "calculator" and implicit_calc:
                matched = True
            if matched:
                params = extractor(message)
                steps.append(
                    ExecutionPlanStep(
                        tool_name=tool_name,
                        parameters=params,
                    )
                )
                logger.info(
                    "Planner: matched tool='%s' params=%s",
                    tool_name,
                    params,
                )

        if not steps:
            plan = ExecutionPlan(
                steps=[],
                tool_name=None,
                parameters={},
                reasoning="No matching tool. Provider responds directly.",
            )
            logger.info("Planner: no tool selected, direct response")
            return plan

        # Backward-compatible fields point to the first step.
        plan = ExecutionPlan(
            steps=steps,
            tool_name=steps[0].tool_name,
            parameters=steps[0].parameters,
            reasoning=(
                f"{len(steps)} tool(s) matched: "
                + ", ".join(s.tool_name for s in steps)
            ),
        )
        logger.info(
            "Planner: %d step(s) planned: %s",
            len(steps),
            [s.tool_name for s in steps],
        )
        return plan


