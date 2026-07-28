"""
expression_normalizer.py
========================
Converts natural language mathematics into valid calculator expressions.

Sprint 3.15.1 - Added fraction patterns
Sprint 3.21   - Added "by" as multiply (for "12 by 8")
              - Added "X% ... on Y" pattern (for "15% tax on 500")
              - Added "multiply X by Y" pattern
              - Added "subtract X from Y" -> "Y - X"
              - Added "add X to Y" -> "Y + X"
              - Added "the result" -> CALC_RESULT placeholder

Transformation Rules
--------------------
  Percentages  : "15% of 340"               -> "340 * (15 / 100)"
               : "15% tax on 500"           -> "500 * (15 / 100)"
  Dimensions   : "12 by 8"                  -> "12 * 8"
  Fractions    : "half of 98"               -> "98 / 2"
  Powers       : "2 raised to the power 8"  -> "2 ^ 8"
  Square roots : "square root of 81"        -> "sqrt(81)"
  References   : "the result"               -> "CALC_RESULT"
               : "subtract it from 500"     -> "500 - CALC_RESULT"
  Word numbers : "three plus four"          -> "3 + 4"
  Operators    : "divided by"               -> "/"

Critical Rules
--------------
  - NEVER translate "%" into modulo when the intent is percentage.
  - ALWAYS convert percentages to (n / 100) multiplication.
  - Pass already-valid expressions through unchanged.
"""

from __future__ import annotations
import re


# ---------------------------------------------------------------------------
# Lookup tables
# ---------------------------------------------------------------------------

_WORD_NUMBERS: dict[str, int] = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30,
    "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90, "hundred": 100, "thousand": 1000,
}

_SIMPLE_FRACTION_WORDS: dict[str, tuple[int, int]] = {
    "half":    (1, 2),
    "third":   (1, 3),
    "quarter": (1, 4),
    "fourth":  (1, 4),
}

_MULTI_FRACTION_WORDS: dict[str, tuple[int, int]] = {
    "one half":       (1, 2),
    "one quarter":    (1, 4),
    "one fourth":     (1, 4),
    "one third":      (1, 3),
    "two thirds":     (2, 3),
    "three quarters": (3, 4),
    "three fourths":  (3, 4),
    "two quarters":   (2, 4),
}

# Multi-word operator aliases — longest first to avoid partial replacement
_OPERATOR_WORDS: list[tuple[str, str]] = [
    ("multiplied by",             "*"),
    ("divided by",                "/"),
    ("raised to the power of",    "^"),
    ("raised to the power",       "^"),
    ("to the power of",           "^"),
    ("plus",                      "+"),
    ("minus",                     "-"),
    ("times",                     "*"),
    ("over",                      "/"),
]

# Conversational prefixes to strip before sqrt matching
_SQRT_PREFIX = re.compile(
    r"^(find|calculate|compute|work\s+out|what\s+is|whats?|evaluate|give\s+me)"
    r"\s+(the\s+)?",
    re.I,
)

# Reference words that map to CALC_RESULT placeholder
_REFERENCE_WORDS = [
    "the result",
    "the answer",
    "the output",
    "that",
    "it",
]


# ---------------------------------------------------------------------------
# Normalizer class
# ---------------------------------------------------------------------------

class ExpressionNormalizer:
    """
    Translates natural language math into a calculator-ready expression.

    Usage:
        n = ExpressionNormalizer()
        n.normalize("15% of 340")           ->  "340 * (15 / 100)"
        n.normalize("12 by 8")              ->  "12 * 8"
        n.normalize("subtract it from 500") ->  "500 - CALC_RESULT"
    """

    def normalize(self, text: str) -> str:
        expr = text.strip().lower()

        # Strip trailing punctuation
        expr = expr.rstrip("?.!")

        # Order matters — more specific patterns run first
        expr = self._strip_sqrt_prefix(expr)
        expr = self._normalize_square_root(expr)
        expr = self._normalize_power_phrases(expr)
        expr = self._normalize_percentage_of(expr)
        expr = self._normalize_percentage_on(expr)       # Sprint 3.21
        expr = self._normalize_multi_fraction_of(expr)
        expr = self._normalize_simple_fraction_of(expr)
        expr = self._normalize_subtract_from(expr)       # Sprint 3.21
        expr = self._normalize_add_to(expr)              # Sprint 3.21
        expr = self._normalize_multiply_by(expr)         # Sprint 3.21
        expr = self._normalize_dimension_by(expr)        # Sprint 3.21
        expr = self._normalize_references(expr)          # Sprint 3.21
        expr = self._normalize_operator_words(expr)
        expr = self._normalize_word_numbers(expr)
        expr = self._clean_whitespace(expr)

        return expr

    # ------------------------------------------------------------------
    # Individual transformations
    # ------------------------------------------------------------------

    def _strip_sqrt_prefix(self, expr: str) -> str:
        return _SQRT_PREFIX.sub("", expr)

    def _normalize_square_root(self, expr: str) -> str:
        expr = re.sub(
            r"(?:square\s+root|sqrt)\s+of\s+([\d.]+)",
            r"sqrt(\1)",
            expr,
        )
        expr = re.sub(
            r"(?:square\s+root|sqrt)\s+([\d.]+)(?!\s*\))",
            r"sqrt(\1)",
            expr,
        )
        return expr

    def _normalize_power_phrases(self, expr: str) -> str:
        patterns = [
            r"(\d+(?:\.\d+)?)\s+raised\s+to\s+(?:the\s+)?power\s+(?:of\s+)?(\d+(?:\.\d+)?)",
            r"(\d+(?:\.\d+)?)\s+to\s+the\s+power\s+of\s+(\d+(?:\.\d+)?)",
            r"(\d+(?:\.\d+)?)\s+to\s+the\s+(\d+)(?:st|nd|rd|th)?\s+power",
            r"(\d+(?:\.\d+)?)\s*\*\*\s*(\d+(?:\.\d+)?)",
        ]
        for p in patterns:
            expr = re.sub(p, r"\1 ^ \2", expr)

        expr = re.sub(r"(\d+(?:\.\d+)?)\s+squared", r"\1 ^ 2", expr)
        expr = re.sub(r"(\d+(?:\.\d+)?)\s+cubed",   r"\1 ^ 3", expr)
        return expr

    def _normalize_percentage_of(self, expr: str) -> str:
        """
        "15% of 340"          ->  "340 * (15 / 100)"
        "15 percent of 340"   ->  "340 * (15 / 100)"
        """
        return re.sub(
            r"([\d.]+)\s*(?:%|percent)\s+of\s+([\d.]+)",
            r"\2 * (\1 / 100)",
            expr,
        )

    def _normalize_percentage_on(self, expr: str) -> str:
        """
        Sprint 3.21: Handle "X% tax/rate/fee on Y" patterns.
        
        "15% tax on 500"      ->  "500 * (15 / 100)"
        "20% rate on 1000"    ->  "1000 * (20 / 100)"
        "5% fee on 200"       ->  "200 * (5 / 100)"
        """
        return re.sub(
            r"([\d.]+)\s*(?:%|percent)\s+(?:tax|rate|fee|discount|markup|margin)?\s*(?:on|of)\s+([\d.]+)",
            r"\2 * (\1 / 100)",
            expr,
        )

    def _normalize_subtract_from(self, expr: str) -> str:
        """
        Sprint 3.21: Handle "subtract X from Y" -> "Y - X"
        Also handles "subtract it/the result from Y" -> "Y - CALC_RESULT"
        
        "subtract 75 from 500"           ->  "500 - 75"
        "subtract it from 500"           ->  "500 - CALC_RESULT"
        "subtract the result from 500"   ->  "500 - CALC_RESULT"
        """
        # First handle explicit numbers
        expr = re.sub(
            r"subtract\s+([\d.]+)\s+from\s+([\d.]+)",
            r"\2 - \1",
            expr,
        )
        # Handle reference words (it, the result, etc.)
        expr = re.sub(
            r"subtract\s+(?:it|the\s+result|the\s+answer|that)\s+from\s+([\d.]+)",
            r"\1 - CALC_RESULT",
            expr,
        )
        return expr

    def _normalize_add_to(self, expr: str) -> str:
        """
        Sprint 3.21: Handle "add X to Y" -> "Y + X"
        Also handles "add X to the result" -> "CALC_RESULT + X"
        
        "add 50 to 100"              ->  "100 + 50"
        "add 50 to the result"       ->  "CALC_RESULT + 50"
        "add 50 to it"               ->  "CALC_RESULT + 50"
        """
        # First handle "add X to the result/it"
        expr = re.sub(
            r"add\s+([\d.]+)\s+to\s+(?:it|the\s+result|the\s+answer|that)",
            r"CALC_RESULT + \1",
            expr,
        )
        # Then handle "add X to Y" (both numbers)
        expr = re.sub(
            r"add\s+([\d.]+)\s+to\s+([\d.]+)",
            r"\2 + \1",
            expr,
        )
        return expr

    def _normalize_multiply_by(self, expr: str) -> str:
        """
        Sprint 3.21: Handle "multiply X by Y" -> "X * Y"
        
        "multiply 120 by 3"          ->  "120 * 3"
        "multiply the result by 45"  ->  "CALC_RESULT * 45"
        """
        # Handle "multiply the result/it by Y"
        expr = re.sub(
            r"multiply\s+(?:it|the\s+result|the\s+answer|that)\s+by\s+([\d.]+)",
            r"CALC_RESULT * \1",
            expr,
        )
        # Handle "multiply X by Y"
        expr = re.sub(
            r"multiply\s+([\d.]+)\s+by\s+([\d.]+)",
            r"\1 * \2",
            expr,
        )
        return expr

    def _normalize_dimension_by(self, expr: str) -> str:
        """
        Sprint 3.21: Handle "X by Y" dimension patterns (e.g., room size).
        
        "12 by 8"        ->  "12 * 8"
        "a 12 by 8"      ->  "12 * 8"
        
        Must run AFTER _normalize_operator_words to avoid breaking
        "divided by" and "multiplied by".
        """
        # Only match standalone "number by number" patterns
        # Negative lookbehind ensures we don't match after "divided" or "multiplied"
        expr = re.sub(
            r"(?<!divided\s)(?<!multiplied\s)(?<![a-z])\b(\d+(?:\.\d+)?)\s+by\s+(\d+(?:\.\d+)?)\b",
            r"\1 * \2",
            expr,
        )
        return expr

    def _normalize_references(self, expr: str) -> str:
        """
        Sprint 3.21: Replace reference words with CALC_RESULT placeholder.
        
        "the result"     ->  "CALC_RESULT"
        "the answer"     ->  "CALC_RESULT"
        
        This runs after specific patterns (subtract from, add to, multiply by)
        to catch any remaining references.
        """
        for ref in _REFERENCE_WORDS:
            expr = re.sub(rf"\b{re.escape(ref)}\b", "CALC_RESULT", expr)
        return expr

    def _normalize_multi_fraction_of(self, expr: str) -> str:
        for phrase, (num, den) in sorted(
            _MULTI_FRACTION_WORDS.items(), key=lambda x: -len(x[0])
        ):
            if num == 1:
                replacement = rf"\1 / {den}"
            else:
                replacement = rf"\1 * ({num} / {den})"

            expr = re.sub(
                rf"(?:a\s+)?{re.escape(phrase)}\s+of\s+([\d.]+)",
                replacement,
                expr,
            )
        return expr

    def _normalize_simple_fraction_of(self, expr: str) -> str:
        for word, (num, den) in _SIMPLE_FRACTION_WORDS.items():
            if num == 1:
                replacement = rf"\1 / {den}"
            else:
                replacement = rf"\1 * ({num} / {den})"

            expr = re.sub(
                rf"(?:a\s+)?{re.escape(word)}\s+of\s+([\d.]+)",
                replacement,
                expr,
            )
        return expr

    def _normalize_operator_words(self, expr: str) -> str:
        """Replace written operators with symbols."""
        for phrase, symbol in _OPERATOR_WORDS:
            expr = re.sub(rf"\b{re.escape(phrase)}\b", symbol, expr)
        return expr

    def _normalize_word_numbers(self, expr: str) -> str:
        """Replace English number words with digits."""
        for word, value in sorted(_WORD_NUMBERS.items(), key=lambda x: -len(x[0])):
            expr = re.sub(rf"\b{re.escape(word)}\b", str(value), expr)
        return expr

    def _clean_whitespace(self, expr: str) -> str:
        """Normalize spacing around operators and remove redundant spaces."""
        expr = re.sub(r"\s*([\+\-\*\/\^])\s*", r" \1 ", expr)
        expr = re.sub(r"sqrt\s*\(\s*(.*?)\s*\)", r"sqrt(\1)", expr)
        expr = re.sub(r"CALC_RESULT", "CALC_RESULT", expr)  # Preserve placeholder
        expr = re.sub(r" {2,}", " ", expr)
        return expr.strip()


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------

_default_normalizer = ExpressionNormalizer()


def normalize_expression(text: str) -> str:
    """
    Normalize a natural language math expression into a calculator expression.

    Args:
        text: Raw input, e.g. "15% of 340" or "subtract it from 500"

    Returns:
        Normalized expression, e.g. "340 * (15 / 100)" or "500 - CALC_RESULT"
    """
    return _default_normalizer.normalize(text)
