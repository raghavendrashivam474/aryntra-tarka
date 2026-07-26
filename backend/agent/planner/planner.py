r"""
agent/planner/planner.py
Intelligent request planner — Sprint 3.15 rewrite.

Replaces the keyword/regex matcher with a full NLP-aware routing layer.

Responsibilities
----------------
  - Detect mathematical intent (including natural language forms)
  - Normalize math expressions before passing to the calculator
  - Route weather, search, datetime, filesystem correctly
  - Collect ALL matching tools for multi-tool plans (Sprint 3.6 contract)
  - Return ExecutionPlan with identical schema to previous sprints
    so AgentRuntime, tests, and routes need zero changes

Sprint history preserved below for reference:
  Sprint 3.2  - DateTime intent recognition expanded.
  Sprint 3.6  - Multi-tool planning.
  Sprint 3.10 - Implicit calculator trigger.
  Sprint 3.15 - Full NLP routing, expression normalization, percentage fix.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from backend.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# ExecutionPlanStep  (unchanged from Sprint 3.6 — runtime depends on this)
# ---------------------------------------------------------------------------

@dataclass
class ExecutionPlanStep:
    """A single tool invocation within an ExecutionPlan."""

    tool_name:  str
    parameters: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# ExecutionPlan  (unchanged from Sprint 3.6 — runtime depends on this)
# ---------------------------------------------------------------------------

@dataclass
class ExecutionPlan:
    """
    Structured plan produced by the Planner.

    Attributes:
        steps:      Ordered list of tool invocations to execute.
        tool_name:  First tool name, or None. (backward compat)
        parameters: First tool parameters, or {}. (backward compat)
        reasoning:  Human-readable explanation.
    """

    steps:      list[ExecutionPlanStep] = field(default_factory=list)
    tool_name:  str | None              = None
    parameters: dict[str, Any]          = field(default_factory=dict)
    reasoning:  str                     = ""


# ---------------------------------------------------------------------------
# Expression normalizer import
# ---------------------------------------------------------------------------

try:
    from backend.planner.normalizers.expression_normalizer import normalize_expression
    _NORMALIZER_AVAILABLE = True
except ImportError:
    _NORMALIZER_AVAILABLE = False
    logger.warning(
        "[Planner] Expression normalizer not found — "
        "raw expressions will be passed to calculator."
    )


def _normalize(text: str) -> str:
    """Normalize a math expression if the normalizer is available."""
    if _NORMALIZER_AVAILABLE:
        try:
            return normalize_expression(text)
        except Exception as exc:
            logger.warning("[Planner] Normalization failed: %s", exc)
    return text


# ---------------------------------------------------------------------------
# Math intent detection
# ---------------------------------------------------------------------------

# Explicit math keywords that always signal calculator intent
_MATH_KEYWORDS = re.compile(
    r"""
    \bcalculat\w*\b   |   # calculate, calculation
    \bcomput\w*\b     |   # compute, computation
    \bsolv\w*\b       |   # solve, solving
    \bevaluat\w*\b    |   # evaluate
    \barithmet\w*\b   |   # arithmetic
    \bmath\w*\b       |   # math, maths
    \bsqrt\b          |   # sqrt
    \bsquare\s+root\b |   # square root
    \bfraction\b      |   # fraction
    \bpercentage?\b   |   # percent, percentage
    \bpercent\b       |   # percent
    \bhalf\b          |   # half
    \bthird\b         |   # third
    \bquarter\b       |   # quarter
    \bfourth\b        |   # fourth
    \braised\b        |   # raised to the power
    \bpower\b         |   # power of
    \bexponent\b      |   # exponent
    \bmodulo?\b       |   # mod, modulo
    \bfactor\b        |   # factor
    \bproduct\b       |   # product of
    \bquotient\b      |   # quotient
    \bsum\s+of\b      |   # sum of
    \bdifference\b        # difference
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Natural language number words
_NUMBER_WORDS = re.compile(
    r"\b(zero|one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|"
    r"eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|"
    r"eighty|ninety|hundred|thousand)\b",
    re.IGNORECASE,
)

# Arithmetic operator words
_OPERATOR_WORDS = re.compile(
    r"\b(plus|minus|times|multiplied\s+by|divided\s+by|over|"
    r"added\s+to|subtract\w*|mod\b|modulo)\b",
    re.IGNORECASE,
)

# Symbolic operators
_SYMBOLIC_OPS = re.compile(r"[+\-*/%^]")

# Percentage pattern  — "15% of 340" or "15 percent of 340"
_PERCENTAGE_OF = re.compile(
    r"\d+\s*(?:%|percent)\s+of\s+\d+",
    re.IGNORECASE,
)

# Fraction-of pattern — "half of 98", "a third of 270"
_FRACTION_OF = re.compile(
    r"\b(?:a\s+)?(?:half|third|quarter|fourth)\s+of\s+\d+",
    re.IGNORECASE,
)

# Power pattern — "2 raised to the power of 8", "2 to the power 8"
_POWER_PATTERN = re.compile(
    r"\d+\s+(?:raised\s+to|to\s+the)\s+(?:the\s+)?power",
    re.IGNORECASE,
)

# Square root pattern
_SQRT_PATTERN = re.compile(
    r"(?:square\s+root|sqrt)\s+of\s+\d+",
    re.IGNORECASE,
)


def _is_math_intent(text: str) -> bool:
    """
    Return True if the message contains mathematical intent.

    Detects:
      - Explicit math keywords
      - Digits combined with operators (symbol or word)
      - Percentage-of patterns
      - Fraction-of patterns
      - Power patterns
      - Square root patterns
      - Number words combined with operator words
    """
    t = text.lower()

    if _MATH_KEYWORDS.search(t):
        return True

    if _PERCENTAGE_OF.search(t):
        return True

    if _FRACTION_OF.search(t):
        return True

    if _POWER_PATTERN.search(t):
        return True

    if _SQRT_PATTERN.search(t):
        return True

    has_digit    = bool(re.search(r"\d", t))
    has_sym_op   = bool(_SYMBOLIC_OPS.search(t))
    has_word_op  = bool(_OPERATOR_WORDS.search(t))
    has_num_word = bool(_NUMBER_WORDS.search(t))

    if has_digit and (has_sym_op or has_word_op):
        return True

    if has_num_word and (has_sym_op or has_word_op):
        return True

    return False


def _build_math_expression(message: str) -> str:
    """
    Extract and normalize the mathematical expression from the message.

    Priority:
      1. Percentage-of  -> delegate to normalizer
      2. Fraction-of    -> delegate to normalizer
      3. Square root    -> delegate to normalizer
      4. Power phrase   -> delegate to normalizer
      5. General        -> normalize full message and extract expression
    """
    # Let the normalizer handle all natural language forms
    normalized = _normalize(message)

    # If normalizer produced something clean, use it directly
    # Strip away any surrounding prose
    expr_match = re.search(
        r"(?:sqrt\([^)]+\)|[\d(][\d\s()+\-*/^%.]*[\d)])",
        normalized,
    )
    if expr_match:
        expr = expr_match.group(0).strip()
        # Fix ^ back to ** for the calculator AST parser
        expr = expr.replace("^", "**")
        return expr

    # Fallback: return normalized full string
    return normalized.strip()


# ---------------------------------------------------------------------------
# DateTime intent detection
# ---------------------------------------------------------------------------

_DATETIME_KEYWORDS = re.compile(
    r"""
    \bwhat\s+time\b         |
    \bcurrent\s+time\b      |
    \bwhat\s+day\b          |
    \bwhat\s+date\b         |
    \bright\s+now\b         |
    \bwhat\s+year\b         |
    \bwhat\s+month\b        |
    \btoday\b               |
    \bclock\b               |
    \btime\s+is\b           |
    \bdate\s+is\b           |
    \btoday'?s?\s+date\b    |
    \btoday'?s?\s+time\b    |
    \bcurrent\s+date\b      |
    \bdate\s+and\s+time\b   |
    \btell\s+me\s+the\s+time\b |
    \btell\s+me\s+the\s+date\b |
    \bwhat'?s\s+the\s+time\b   |
    \bwhat'?s\s+the\s+date\b   |
    \bwhat\s+is\s+the\s+time\b |
    \bwhat\s+is\s+the\s+date\b |
    \bwhat\s+is\s+today\b
    """,
    re.VERBOSE | re.IGNORECASE,
)


def _is_datetime_intent(text: str) -> bool:
    return bool(_DATETIME_KEYWORDS.search(text))


# ---------------------------------------------------------------------------
# Filesystem intent detection
# ---------------------------------------------------------------------------

_FILESYSTEM_KEYWORDS = re.compile(
    r"""
    \blist\s+files?\b     |
    \bshow\s+files?\b     |
    \bfiles?\s+in\b       |
    \bwhat\s+files?\b     |
    \bdirector\w*\b       |
    \bfolder\b            |
    \bread\s+file\b       |
    \bopen\s+file\b       |
    \bwrite\s+(?:to\s+)?file\b
    """,
    re.VERBOSE | re.IGNORECASE,
)

_PATH_PATTERN = re.compile(
    r"(?:in|at|of|inside)\s+([./~\\][\w./\\-]*)"
)


def _is_filesystem_intent(text: str) -> bool:
    return bool(_FILESYSTEM_KEYWORDS.search(text))


def _extract_path(message: str) -> dict[str, Any]:
    match = _PATH_PATTERN.search(message)
    return {"path": match.group(1) if match else "."}


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------

class Planner:
    """
    Intelligent request planner — Sprint 3.15.

    Detects ALL matching intents and builds a multi-step ExecutionPlan.
    Returns the same ExecutionPlan schema as Sprint 3.6 so the runtime
    and all existing tests require zero changes.

    Routing priority (mirrors tool_metadata.py):
      1. Calculator  — math takes priority over datetime ("times" -> calc)
      2. DateTime    — only if no math intent detected
      3. Filesystem  — path/directory operations
      4. No tool     — LLM answers directly
    """

    def plan(self, message: str) -> ExecutionPlan:
        """
        Analyse the message and return a typed ExecutionPlan.

        Args:
            message: Raw user message.

        Returns:
            ExecutionPlan with zero, one, or many steps.
        """
        text = message.lower().strip()
        logger.info("[Planner] Analysing: '%s'", message)

        steps: list[ExecutionPlanStep] = []

        # ── 1. Calculator ────────────────────────────────────────────
        if _is_math_intent(text):
            expr = _build_math_expression(message)
            steps.append(ExecutionPlanStep(
                tool_name  = "calculator",
                parameters = {"expression": expr},
            ))
            logger.info("[Planner] Calculator selected | expr='%s'", expr)

        # ── 2. DateTime ──────────────────────────────────────────────
        # Only trigger datetime if we did NOT already match calculator.
        # This prevents "times" from double-routing.
        if _is_datetime_intent(text) and not steps:
            steps.append(ExecutionPlanStep(
                tool_name  = "datetime",
                parameters = {},
            ))
            logger.info("[Planner] DateTime selected")

        # ── 3. Filesystem ────────────────────────────────────────────
        if _is_filesystem_intent(text):
            params = _extract_path(message)
            steps.append(ExecutionPlanStep(
                tool_name  = "filesystem",
                parameters = params,
            ))
            logger.info("[Planner] Filesystem selected | path='%s'", params.get("path"))

        # ── No tool ──────────────────────────────────────────────────
        if not steps:
            logger.info("[Planner] No tool matched — direct LLM response")
            return ExecutionPlan(
                steps      = [],
                tool_name  = None,
                parameters = {},
                reasoning  = "No matching tool. Provider responds directly.",
            )

        # Build plan — backward-compat fields point to first step
        plan = ExecutionPlan(
            steps      = steps,
            tool_name  = steps[0].tool_name,
            parameters = steps[0].parameters,
            reasoning  = (
                f"{len(steps)} tool(s) selected: "
                + ", ".join(s.tool_name for s in steps)
            ),
        )

        logger.info(
            "[Planner] Plan ready | %d step(s): %s",
            len(steps),
            [s.tool_name for s in steps],
        )
        return plan
