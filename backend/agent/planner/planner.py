r"""
agent/planner/planner.py
Intelligent request planner.

Sprint 3.21:
  - _build_math_expression rewritten — removed fragile regex extraction.
  - Added multiply, add, subtract to math intent detection.
  - Added multiply by, add to operator words.
  - Added prose stripping after normalization to prevent calculator
    receiving sentences like 'the area of a 12 * 8 room'.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from backend.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# ExecutionPlanStep
# ---------------------------------------------------------------------------

@dataclass
class ExecutionPlanStep:
    """A single tool invocation within an ExecutionPlan."""
    tool_name:  str
    parameters: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# ExecutionPlan
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

_SYMBOLIC_OPS = re.compile(r"[+\-*/%^]")

_PERCENTAGE_OF = re.compile(
    r"\d+\s*(?:%|percent)\s+(?:of|on|tax|rate)\s+\d+",
    re.IGNORECASE,
)

_FRACTION_OF = re.compile(
    r"\b(?:a\s+)?(?:half|third|quarter|fourth)\s+of\s+\d+",
    re.IGNORECASE,
)

_POWER_PATTERN = re.compile(
    r"\d+\s+(?:raised\s+to|to\s+the)\s+(?:the\s+)?power",
    re.IGNORECASE,
)

_SQRT_PATTERN = re.compile(
    r"(?:square\s+root|sqrt)\s+of\s+\d+",
    re.IGNORECASE,
)

# Detects dimension pattern: "12 by 8", "a 5 by 3"
_DIMENSION_PATTERN = re.compile(
    r"\d+\s+by\s+\d+",
    re.IGNORECASE,
)

# Conversational prefixes to strip
_CONVERSATIONAL_PREFIX = re.compile(
    r"^(what\s+is|what'?s|calculate|compute|evaluate|find|work\s+out|"
    r"solve|tell\s+me|give\s+me|please\s+calculate|please\s+compute)\s+",
    re.IGNORECASE,
)

# After normalization, extract only the math-valid portion.
# Matches expressions that contain numbers and operators,
# including CALC_RESULT placeholder.
# This strips surrounding prose like "the area of a ... room".
_MATH_EXTRACT = re.compile(
    r"(CALC_RESULT[\s\d\s()+\-*/^%.CALC_RESULT]*|"
    r"[\d(][\d\s()+\-*/^%.]*[\d)]|"
    r"sqrt\([^)]+\))",
)


def _is_math_intent(text: str) -> bool:
    """Return True if the message contains mathematical intent."""
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
    if _DIMENSION_PATTERN.search(t):
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


def _extract_math_from_normalized(normalized: str) -> str:
    """
    Extract the math-valid portion from a normalized expression.

    After normalization, prose words may still surround the numeric
    expression. For example:
        'the area of a 12 * 8 room' -> '12 * 8'
        '500 * (15 / 100)'          -> '500 * (15 / 100)'  (unchanged)
        'CALC_RESULT * 45'          -> 'CALC_RESULT * 45'  (unchanged)

    Strategy:
      1. If the expression contains CALC_RESULT, extract around it.
      2. Find the longest contiguous math substring.
      3. Fall back to the full normalized string if nothing found.
    """
    # If CALC_RESULT placeholder is present, extract it with its context
    if "CALC_RESULT" in normalized:
        # Extract the full expression containing CALC_RESULT
        match = re.search(
            r"(CALC_RESULT\s*[\+\-\*\/]\s*[\d.]+|"
            r"[\d.]+\s*[\+\-\*\/]\s*CALC_RESULT|"
            r"CALC_RESULT)",
            normalized,
        )
        if match:
            return match.group(0).strip()

    # Find the longest math substring (numbers + operators + parens)
    matches = list(_MATH_EXTRACT.finditer(normalized))
    if matches:
        # Return the longest match — this is most likely the full expression
        best = max(matches, key=lambda m: len(m.group(0)))
        return best.group(0).strip()

    # No extractable math — return as-is and let AST parser reject it
    return normalized.strip()


def _build_math_expression(message: str) -> str:
    """
    Build a calculator-ready expression from the message.

    Sprint 3.21 — deterministic rewrite:
      1. Strip conversational prefix.
      2. Normalize natural language to math symbols.
      3. Extract the math-valid portion, stripping surrounding prose.
      4. Replace ^ with ** for AST parser.
      5. Return clean expression.
    """
    # Strip conversational prefix
    cleaned = _CONVERSATIONAL_PREFIX.sub("", message.strip())

    # Normalize natural language
    normalized = _normalize(cleaned)

    # Extract math-valid portion — strip prose
    expr = _extract_math_from_normalized(normalized)

    # Strip trailing punctuation
    expr = expr.strip().rstrip("?.!")

    # Ensure caret is converted to Python power operator
    expr = expr.replace("^", "**")

    logger.debug("[Planner] Built expression: '%s' from: '%s'", expr, message)

    return expr.strip()


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
    \bwhat\s+is\s+today\b      |
    \btime\b                   |
    \bdate\b         |
    \btime\b                |
    \bdate\b
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
    Intelligent request planner — Sprint 3.21.

    Routing priority:
      1. Calculator  — math takes priority over datetime
      2. DateTime    — only if no math intent detected
      3. Filesystem  — path/directory operations
      4. No tool     — LLM answers directly
    """

    def plan(self, message: str) -> ExecutionPlan:
        """
        Analyse the message and return a typed ExecutionPlan.

        Args:
            message: Raw user message or goal description.

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
        # Add datetime alongside calculator when both intents are present.
        # Only suppress datetime if steps exist AND no explicit datetime keyword found.
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
            logger.info(
                "[Planner] Filesystem selected | path='%s'",
                params.get("path"),
            )

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





