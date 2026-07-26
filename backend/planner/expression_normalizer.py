"""
Expression Normalizer - Sprint 3.15
Translate natural-language math into calculator expressions.
"""
import re
from typing import Optional


class ExpressionNormalizer:
    # Order matters: more specific patterns first.
    PATTERNS = [
        # "X% of Y" -> "Y * (X / 100)"
        (re.compile(r'(\d+(?:\.\d+)?)\s*%\s*of\s*(\d+(?:\.\d+)?)', re.I),
         lambda m: f"{m.group(2)} * ({m.group(1)} / 100)"),

        # "half of X"
        (re.compile(r'half\s+of\s+(\d+(?:\.\d+)?)', re.I),
         lambda m: f"{m.group(1)} / 2"),

        # "third of X"
        (re.compile(r'(?:one[- ])?third\s+of\s+(\d+(?:\.\d+)?)', re.I),
         lambda m: f"{m.group(1)} / 3"),

        # "quarter of X"
        (re.compile(r'(?:one[- ])?quarter\s+of\s+(\d+(?:\.\d+)?)', re.I),
         lambda m: f"{m.group(1)} / 4"),

        # "square root of X"
        (re.compile(r'square\s+root\s+of\s+(\d+(?:\.\d+)?)', re.I),
         lambda m: f"sqrt({m.group(1)})"),

        # "cube root of X"
        (re.compile(r'cube\s+root\s+of\s+(\d+(?:\.\d+)?)', re.I),
         lambda m: f"({m.group(1)}) ^ (1/3)"),

        # "X raised to the power Y" / "X to the power of Y"
        (re.compile(r'(\d+(?:\.\d+)?)\s+(?:raised\s+to\s+the\s+power|to\s+the\s+power\s+of)\s+(\d+(?:\.\d+)?)', re.I),
         lambda m: f"{m.group(1)} ^ {m.group(2)}"),

        # "X squared"
        (re.compile(r'(\d+(?:\.\d+)?)\s+squared', re.I),
         lambda m: f"{m.group(1)} ^ 2"),

        # "X cubed"
        (re.compile(r'(\d+(?:\.\d+)?)\s+cubed', re.I),
         lambda m: f"{m.group(1)} ^ 3"),

        # words to operators
        (re.compile(r'\s+plus\s+', re.I), lambda m: " + "),
        (re.compile(r'\s+minus\s+', re.I), lambda m: " - "),
        (re.compile(r'\s+times\s+', re.I), lambda m: " * "),
        (re.compile(r'\s+multiplied\s+by\s+', re.I), lambda m: " * "),
        (re.compile(r'\s+divided\s+by\s+', re.I), lambda m: " / "),
        (re.compile(r'\s*[×✕]\s*'), lambda m: " * "),
        (re.compile(r'\s*÷\s*'), lambda m: " / "),
    ]

    MATH_HINT = re.compile(
        r'(\d)|percent|%|plus|minus|times|divided|square|cube|power|sqrt|half|quarter|third|raised|multiplied',
        re.I
    )

    @classmethod
    def looks_like_math(cls, text: str) -> bool:
        return bool(cls.MATH_HINT.search(text))

    @classmethod
    def normalize(cls, text: str) -> Optional[str]:
        """Return a calculator-safe expression, or None if not math."""
        if not cls.looks_like_math(text):
            return None
        out = text.strip().rstrip('?.!')
        # Strip common prefixes
        out = re.sub(r'^(what\s+is|calculate|compute|whats|what\'s)\s+',
                     '', out, flags=re.I)
        for pat, repl in cls.PATTERNS:
            out = pat.sub(repl, out)
        # Cleanup whitespace
        out = re.sub(r'\s+', ' ', out).strip()
        return out if out else None
