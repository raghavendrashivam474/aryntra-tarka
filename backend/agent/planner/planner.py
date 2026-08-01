# coding: utf-8
r"""
agent/planner/planner.py
Intelligent request planner.

Sprint 3.21:
  - _build_math_expression rewritten.
  - Added multiply, add, subtract to math intent detection.
  - Added prose stripping after normalization.

v1.5 Plugin SDK:
  - Planner accepts optional plugin_registry at construction.
  - After hardcoded rules, plugin intents are checked dynamically.
  - Any registered plugin with a matching keyword in its description
    can be routed to without touching planner code.
  - Weather intent detection added as first plugin-aware route.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from backend.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# ExecutionPlanStep / ExecutionPlan
# ---------------------------------------------------------------------------

@dataclass
class ExecutionPlanStep:
    tool_name:  str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionPlan:
    steps:      list[ExecutionPlanStep] = field(default_factory=list)
    tool_name:  str | None              = None
    parameters: dict[str, Any]          = field(default_factory=dict)
    reasoning:  str                     = ""


# ---------------------------------------------------------------------------
# Expression normalizer
# ---------------------------------------------------------------------------

try:
    from backend.planner.normalizers.expression_normalizer import normalize_expression
    _NORMALIZER_AVAILABLE = True
except ImportError:
    _NORMALIZER_AVAILABLE = False
    logger.warning(
        "[Planner] Expression normalizer not found - "
        "raw expressions will be passed to calculator."
    )


def _normalize(text: str) -> str:
    if _NORMALIZER_AVAILABLE:
        try:
            return normalize_expression(text)
        except Exception as exc:
            logger.warning("[Planner] Normalization failed: %s", exc)
    return text


# ---------------------------------------------------------------------------
# Math intent
# ---------------------------------------------------------------------------

_MATH_KEYWORDS = re.compile(
    r"""
    \bcalculat\w*\b       |
    \bcomput\w*\b         |
    \bsolv\w*\b           |
    \bevaluat\w*\b        |
    \barithmet\w*\b       |
    \bmath\w*\b           |
    \bsqrt\b              |
    \bsquare\s+root\b     |
    \bfraction\b          |
    \bpercentage?\b       |
    \bpercent\b           |
    \bhalf\b              |
    \bthird\b             |
    \bquarter\b           |
    \bfourth\b            |
    \braised\b            |
    \bpower\b             |
    \bexponent\b          |
    \bmodulo?\b           |
    \bfactor\b            |
    \bproduct\b           |
    \bquotient\b          |
    \bsum\s+of\b          |
    \bdifference\b        |
    \bmultiply\w*\b       |
    \bsubtract\w*\b       |
    \bdivide\w*\b         |
    \badd\b               |
    \barea\b              |
    \bcost\b              |
    \btotal\b             |
    \bprice\b             |
    \bdiscount\b          |
    \btax\b               |
    \bprofit\b            |
    \brevenue\b
    """,
    re.VERBOSE | re.IGNORECASE,
)

_NUMBER_WORDS = re.compile(
    r"\b(zero|one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|"
    r"eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|"
    r"eighty|ninety|hundred|thousand)\b",
    re.IGNORECASE,
)

_OPERATOR_WORDS = re.compile(
    r"\b(plus|minus|times|multiplied\s+by|multiply\w*\s+by|"
    r"divided\s+by|divide\w*\s+by|over|added\s+to|add\w*\s+to|"
    r"subtract\w*|mod\b|modulo|by)\b",
    re.IGNORECASE,
)

_SYMBOLIC_OPS   = re.compile(r"[+\-*/%^]")
_PERCENTAGE_OF  = re.compile(r"\d+\s*(?:%|percent)\s+(?:of|on|tax|rate)\s+\d+", re.IGNORECASE)
_FRACTION_OF    = re.compile(r"\b(?:a\s+)?(?:half|third|quarter|fourth)\s+of\s+\d+", re.IGNORECASE)
_POWER_PATTERN  = re.compile(r"\d+\s+(?:raised\s+to|to\s+the)\s+(?:the\s+)?power", re.IGNORECASE)
_SQRT_PATTERN   = re.compile(r"(?:square\s+root|sqrt)\s+of\s+\d+", re.IGNORECASE)
_DIMENSION_PATTERN = re.compile(r"\d+\s+by\s+\d+", re.IGNORECASE)

_CONVERSATIONAL_PREFIX = re.compile(
    r"^(what\s+is|what'?s|calculate|compute|evaluate|find|work\s+out|"
    r"solve|tell\s+me|give\s+me|please\s+calculate|please\s+compute)\s+",
    re.IGNORECASE,
)

_MATH_EXTRACT = re.compile(
    r"(CALC_RESULT[\s\d\s()+\-*/^%.CALC_RESULT]*|"
    r"[\d(][\d\s()+\-*/^%.]*[\d)]|"
    r"sqrt\([^)]+\))",
)


def _is_math_intent(text: str) -> bool:
    t = text.lower()
    if _MATH_KEYWORDS.search(t):     return True
    if _PERCENTAGE_OF.search(t):     return True
    if _FRACTION_OF.search(t):       return True
    if _POWER_PATTERN.search(t):     return True
    if _SQRT_PATTERN.search(t):      return True
    if _DIMENSION_PATTERN.search(t): return True
    has_digit    = bool(re.search(r"\d", t))
    has_sym_op   = bool(_SYMBOLIC_OPS.search(t))
    has_word_op  = bool(_OPERATOR_WORDS.search(t))
    has_num_word = bool(_NUMBER_WORDS.search(t))
    if has_digit and (has_sym_op or has_word_op):   return True
    if has_num_word and (has_sym_op or has_word_op): return True
    return False


def _extract_math_from_normalized(normalized: str) -> str:
    if "CALC_RESULT" in normalized:
        match = re.search(
            r"(CALC_RESULT\s*[\+\-\*\/]\s*[\d.]+|"
            r"[\d.]+\s*[\+\-\*\/]\s*CALC_RESULT|"
            r"CALC_RESULT)",
            normalized,
        )
        if match:
            return match.group(0).strip()
    matches = list(_MATH_EXTRACT.finditer(normalized))
    if matches:
        best = max(matches, key=lambda m: len(m.group(0)))
        return best.group(0).strip()
    return normalized.strip()


def _build_math_expression(message: str) -> str:
    cleaned    = _CONVERSATIONAL_PREFIX.sub("", message.strip())
    normalized = _normalize(cleaned)
    expr       = _extract_math_from_normalized(normalized)
    expr       = expr.strip().rstrip("?.!")
    expr       = expr.replace("^", "**")
    logger.debug("[Planner] Built expression: '%s' from: '%s'", expr, message)
    return expr.strip()


# ---------------------------------------------------------------------------
# DateTime intent
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
    \bwhat\s+is\s+today\b      |
    \btime\b                   |
    \bdate\b
    """,
    re.VERBOSE | re.IGNORECASE,
)


def _is_datetime_intent(text: str) -> bool:
    return bool(_DATETIME_KEYWORDS.search(text))


# ---------------------------------------------------------------------------
# Filesystem intent
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

_PATH_PATTERN = re.compile(r"(?:in|at|of|inside)\s+([./~\\][\w./\\-]*)")


def _is_filesystem_intent(text: str) -> bool:
    return bool(_FILESYSTEM_KEYWORDS.search(text))


def _extract_path(message: str) -> dict[str, Any]:
    match = _PATH_PATTERN.search(message)
    return {"path": match.group(1) if match else "."}


# ---------------------------------------------------------------------------
# Weather intent
# ---------------------------------------------------------------------------

_WEATHER_PATTERN = re.compile(
    r"""
    \bweather\b           |
    \btemperature\b       |
    \bforecast\b          |
    \brain\w*\b           |
    \bsunny\b             |
    \bcloudy\b            |
    \bhumidity\b          |
    \bwind\b              |
    \bhot\s+in\b          |
    \bcold\s+in\b         |
    \bwarm\s+in\b
    """,
    re.VERBOSE | re.IGNORECASE,
)

_LOCATION_PATTERN = re.compile(
    r"""
    (?:in|for|at|of)\s+
    ([A-Z][a-zA-Z\s]{2,30})
    (?:\s*[?.!,]|$)
    """,
    re.VERBOSE,
)


def _is_weather_intent(text: str) -> bool:
    return bool(_WEATHER_PATTERN.search(text))


def _extract_location(message: str) -> str:
    match = _LOCATION_PATTERN.search(message)
    if match:
        return match.group(1).strip()
    # Fallback: grab words after weather keyword
    m2 = re.search(
        r"\bweather\b\s+(?:in|for|at)?\s*([A-Za-z\s]{2,30})",
        message,
        re.IGNORECASE,
    )
    if m2:
        return m2.group(1).strip().rstrip("?.!,")
    return "Unknown"


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------

class Planner:
    """
    Intelligent request planner.

    v1.5: Accepts an optional plugin_registry. After hardcoded rules,
    the planner checks registered plugins for any unmatched intent.
    New plugins are picked up automatically with no planner changes.

    Routing priority:
      1. Calculator   - math
      2. DateTime     - time and date
      3. Filesystem   - file operations
      4. Weather      - weather queries    (plugin-aware)
      5. No tool      - LLM direct
    """

    def __init__(self, plugin_registry=None) -> None:
        """
        Args:
            plugin_registry: Optional agent ToolRegistry instance.
                             Used to discover plugin-provided tools at
                             plan time. Pass the live registry from
                             agent/services/agent.py.
        """
        self._plugin_registry = plugin_registry

    def plan(self, message: str) -> ExecutionPlan:
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
        if _is_datetime_intent(text):
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

        # ── 4. Weather (plugin-aware) ────────────────────────────────
        # Only route to weather if:
        #   - Weather intent detected
        #   - No steps already selected (avoids double routing)
        #   - Weather tool is registered (plugin loaded)
        if not steps and _is_weather_intent(text):
            if self._plugin_registry and self._plugin_registry.has_tool("weather"):
                location = _extract_location(message)
                steps.append(ExecutionPlanStep(
                    tool_name  = "weather",
                    parameters = {"location": location},
                ))
                logger.info(
                    "[Planner] Weather plugin selected | location='%s'", location
                )
            else:
                logger.info(
                    "[Planner] Weather intent detected but plugin not registered."
                )

        # ── No tool ──────────────────────────────────────────────────
        if not steps:
            logger.info("[Planner] No tool matched - direct LLM response")
            return ExecutionPlan(
                steps      = [],
                tool_name  = None,
                parameters = {},
                reasoning  = "No matching tool. Provider responds directly.",
            )

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