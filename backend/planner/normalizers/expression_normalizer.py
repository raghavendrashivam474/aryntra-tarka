"""
expression_normalizer.py
========================
Converts natural language mathematics into valid calculator expressions.

Transformation Rules
--------------------
  Percentages  : "15% of 340"               -> "340 * (15 / 100)"
  Fractions    : "half of 98"               -> "98 / 2"
  Powers       : "2 raised to the power 8"  -> "2 ^ 8"
  Square roots : "square root of 81"        -> "sqrt(81)"
  Word numbers : "three plus four"          -> "3 + 4"
  Operator words: "divided by"             -> "/"

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

# fraction-word -> (numerator, denominator)
_FRACTION_WORDS: dict[str, tuple[int, int]] = {
    "half":    (1, 2),
    "third":   (1, 3),
    "quarter": (1, 4),
    "fourth":  (1, 4),
}

# multi-word operator aliases (longest first to avoid partial replacement)
_OPERATOR_WORDS: list[tuple[str, str]] = [
    ("multiplied by",  "*"),
    ("divided by",     "/"),
    ("raised to the power of", "^"),
    ("raised to the power",    "^"),
    ("to the power of",        "^"),
    ("plus",                   "+"),
    ("minus",                  "-"),
    ("times",                  "*"),
    ("over",                   "/"),
]


# ---------------------------------------------------------------------------
# Normalizer class
# ---------------------------------------------------------------------------

class ExpressionNormalizer:
    """
    Translates natural language math into a calculator-ready expression.

    Usage:
        n = ExpressionNormalizer()
        n.normalize("15% of 340")  ->  "340 * (15 / 100)"
    """

    def normalize(self, text: str) -> str:
        expr = text.strip().lower()

        expr = self._normalize_square_root(expr)
        expr = self._normalize_power_phrases(expr)
        expr = self._normalize_percentage_of(expr)
        expr = self._normalize_fraction_of(expr)
        expr = self._normalize_operator_words(expr)
        expr = self._normalize_word_numbers(expr)
        expr = self._clean_whitespace(expr)

        return expr

    # ------------------------------------------------------------------
    # Individual transformations
    # ------------------------------------------------------------------

    def _normalize_square_root(self, expr: str) -> str:
        """
        "square root of 81"  ->  "sqrt(81)"
        "sqrt of 144"        ->  "sqrt(144)"
        """
        return re.sub(
            r"(?:square\s+root|sqrt)\s+of\s+([\d.]+)",
            r"sqrt(\1)",
            expr,
        )

    def _normalize_power_phrases(self, expr: str) -> str:
        """
        "2 raised to the power 8"  ->  "2 ^ 8"
        "2 to the power of 8"      ->  "2 ^ 8"
        "2 to the 8th power"       ->  "2 ^ 8"
        "2 ** 8"                   ->  "2 ^ 8"   (Python-style)
        """
        patterns = [
            r"(\d+(?:\.\d+)?)\s+raised\s+to\s+(?:the\s+)?power\s+(?:of\s+)?(\d+(?:\.\d+)?)",
            r"(\d+(?:\.\d+)?)\s+to\s+the\s+power\s+of\s+(\d+(?:\.\d+)?)",
            r"(\d+(?:\.\d+)?)\s+to\s+the\s+(\d+)(?:st|nd|rd|th)?\s+power",
            r"(\d+(?:\.\d+)?)\s*\*\*\s*(\d+(?:\.\d+)?)",
        ]
        for p in patterns:
            expr = re.sub(p, r"\1 ^ \2", expr)
        return expr

    def _normalize_percentage_of(self, expr: str) -> str:
        """
        "15% of 340"          ->  "340 * (15 / 100)"
        "15 percent of 340"   ->  "340 * (15 / 100)"

        This MUST run before any lone-% handling to prevent modulo confusion.
        """
        return re.sub(
            r"([\d.]+)\s*(?:%|percent)\s+of\s+([\d.]+)",
            r"\2 * (\1 / 100)",
            expr,
        )

    def _normalize_fraction_of(self, expr: str) -> str:
        """
        "half of 98"     ->  "98 / 2"
        "a third of 60"  ->  "60 / 3"
        "quarter of 80"  ->  "80 / 4"
        """
        for word, (num, den) in _FRACTION_WORDS.items():
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
        # Pad operators for readability
        expr = re.sub(r"\s*([\+\-\*\/\^])\s*", r" \1 ", expr)
        # But don't double-space inside sqrt(...)
        expr = re.sub(r"sqrt\s*\(\s*(.*?)\s*\)", r"sqrt(\1)", expr)
        # Collapse multiple spaces
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
        text: Raw input, e.g. "15% of 340" or "square root of 81"

    Returns:
        Normalized expression, e.g. "340 * (15 / 100)" or "sqrt(81)"
    """
    return _default_normalizer.normalize(text)
