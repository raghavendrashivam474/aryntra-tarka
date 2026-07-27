"""
intent_classifier.py
====================
Sprint 3.15.1 — Intent Classification Layer

Sprint 3.15.1 patch 1
---------------------
  Fix 1: Search pattern now allows intervening words between
          "latest/breaking/current/recent" and "news/events/updates".
          "Latest AI news" now correctly classifies as SEARCH.

  Fix 2: Explicit search verb ("search", "look up", "find out about")
          is checked BEFORE the datetime gate so that
          "Search for Bitcoin price today" routes to SEARCH not DATETIME.
          The bare "today" datetime pattern is tightened to require
          a time/date noun alongside it.

All other logic preserved exactly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Intent:
    """
    Classification result.

    Attributes:
        type       : One of the intent type constants defined below.
        confidence : 0.0 - 1.0 estimate of classifier certainty.
        reason     : Human-readable explanation for logging/debugging.
    """
    type:       str
    confidence: float
    reason:     str = ""

    def __str__(self) -> str:
        return f"Intent(type={self.type!r}, confidence={self.confidence:.2f})"


# ---------------------------------------------------------------------------
# Intent type constants
# ---------------------------------------------------------------------------

CALCULATION  = "CALCULATION"
EXPLANATION  = "EXPLANATION"
FACT_LOOKUP  = "FACT_LOOKUP"
DATETIME     = "DATETIME"
WEATHER      = "WEATHER"
SEARCH       = "SEARCH"
FILE         = "FILE"
PASSWORD     = "PASSWORD"
SYSTEM       = "SYSTEM"
GENERAL      = "GENERAL"


# ---------------------------------------------------------------------------
# Pattern banks
# ---------------------------------------------------------------------------

# Phrases that unambiguously signal a conceptual / educational request.
# These patterns take priority over ALL tool routing.
_EXPLANATION_PATTERNS: list[re.Pattern] = [
    re.compile(r"^(explain|describing?|tell\s+me\s+about|what\s+is\s+a\b|what\s+are\b)", re.I),
    re.compile(r"^how\s+(does|do|did|would|can|could|should|is|are)\b", re.I),
    re.compile(r"^why\s+(does|do|did|is|are|would|can|could)\b", re.I),
    re.compile(r"^what\s+(does\s+\w+\s+mean|is\s+the\s+(concept|definition|meaning|idea|theory|principle|purpose|difference|relationship))", re.I),
    re.compile(r"^what\s+is\s+(recursion|a\s+\w+|the\s+(formula|concept|definition|meaning|theory|principle|difference|purpose|idea))\b", re.I),
    re.compile(r"(formula|concept|definition|theorem|principle|theory|algorithm)\s+(for|of|behind|about)", re.I),
    re.compile(r"^(describe|elaborate|summarize|overview|introduction\s+to)\b", re.I),
    re.compile(r"\bmean\s+in\s+(mathematics|math|computing|physics|science|programming)\b", re.I),
    re.compile(r"\b(what\s+is|what\s+does)\b.*(mean|means|represent|stands?\s+for)\b", re.I),
    re.compile(r"^what\s+is\s+the\s+(formula|rule|method|technique|approach|way)\b", re.I),
]

# Phrases that indicate the user wants an actual computation performed.
_CALCULATION_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(calculate|compute|evaluate|work\s+out|solve|find\s+the\s+value)\b", re.I),
    re.compile(r"\d+\s*[\+\-\*\/\^]\s*\d+", re.I),
    re.compile(r"\d+\s*%\s*(of)\s*\d+", re.I),
    re.compile(r"\d+\s*(percent)\s+of\s+\d+", re.I),
    re.compile(r"(half|quarter|third|fourth)\s+of\s+\d+", re.I),
    re.compile(r"(a\s+)?(quarter|half|third)\s+of\s+\d+", re.I),
    re.compile(r"(three|two)\s+quarters?\s+of\s+\d+", re.I),
    re.compile(r"\b(square\s+root|sqrt|cube\s+root)\s+(of\s+)?\d+", re.I),
    re.compile(r"\bfind\s+the\s+(sqrt|square\s+root|cube\s+root)\b", re.I),
    re.compile(r"\d+\s+(squared|cubed|raised|to\s+the\s+power)", re.I),
    re.compile(r"\b(what\s+is|whats?)\s+\d+", re.I),
    re.compile(r"\b\d+\s+(plus|minus|times|divided\s+by|multiplied\s+by)\s+\d+\b", re.I),
]

# ---------------------------------------------------------------------------
# Fix 1: Search patterns
# ---------------------------------------------------------------------------
# Pattern A: explicit search verb — highest confidence, checked early
# Pattern B: recency word + optional gap + news noun (allows "Latest AI news")
# Pattern C: live data signals (price, score, ranking)

_SEARCH_VERB_PATTERN = re.compile(
    r"\b(search|look\s+up|find\s+out\s+about)\b",
    re.I,
)

_SEARCH_PATTERNS: list[re.Pattern] = [
    # recency word ... news noun — allows up to 5 words between them
    re.compile(
        r"\b(latest|breaking|current|recent|today'?s?)\b.{0,40}"
        r"\b(news|events?|updates?|stories|headlines?)\b",
        re.I,
    ),
    # live data nouns
    re.compile(r"\b(price|stock|score|ranking|standings?)\b", re.I),
]

# ---------------------------------------------------------------------------
# Fix 2: Datetime patterns — tightened so bare "today" without a time/date
# noun does NOT fire when a search verb is also present.
# The bare-"today" pattern is now only matched in the datetime gate AFTER
# confirming no search verb precedes it.
# ---------------------------------------------------------------------------

# Strong datetime: explicit time/date noun present
_DATETIME_STRONG_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(current\s+)?(time|date|day|month|year)\b", re.I),
    re.compile(r"\bwhat('?s|\s+is)\s+(today|the\s+time|the\s+date)\b", re.I),
    re.compile(r"\bright\s+now\b", re.I),
]

# Weak datetime: bare "today" — only used when no search verb present
_DATETIME_WEAK_TODAY = re.compile(r"\btoday\b", re.I)

# Weather signals
_WEATHER_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bweather\b", re.I),
    re.compile(r"\b(temperature|humidity|forecast|raining|sunny|cold|hot|wind)\b", re.I),
    re.compile(r"\bweather\s+(in|at|for)\b", re.I),
]

# File system signals
_FILE_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(read|write|save|open|delete|list|rename)\s+(file|files|directory|folder)\b", re.I),
    re.compile(r"\bfile\s+(at|in|from|called|named)\b", re.I),
    re.compile(r"\b(\/[a-z]|[A-Z]:\\)", re.I),
]

# Password signals
_PASSWORD_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(generate|create|make|give\s+me)\b.{0,30}\bpassword\b", re.I),
    re.compile(r"\bpassword\b.{0,20}\b(generate|create|random|secure|strong)\b", re.I),
]

# System info signals
_SYSTEM_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(cpu|ram|memory|disk\s+space|operating\s+system|os|uptime|system\s+info)\b", re.I),
]


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

class IntentClassifier:
    """
    Rule-based intent classifier.

    Priority order (highest first):
      1. EXPLANATION  — conceptual phrasing overrides everything
      2. CALCULATION  — numeric/compute intent
      3. SEARCH (verb) — explicit search verb checked before datetime
      4. DATETIME     — time/date queries
      5. WEATHER      — weather queries
      6. SEARCH (noun) — recency/news signals
      7. FILE         — file operations
      8. PASSWORD     — password generation
      9. SYSTEM       — system information
      10. GENERAL     — fallback
    """

    def classify(self, text: str) -> Intent:
        stripped = text.strip()

        # ------------------------------------------------------------------
        # Gate 1 — EXPLANATION (highest priority)
        # ------------------------------------------------------------------
        for pat in _EXPLANATION_PATTERNS:
            if pat.search(stripped):
                has_calc = any(p.search(stripped) for p in _CALCULATION_PATTERNS)
                if not has_calc:
                    return Intent(
                        type=EXPLANATION,
                        confidence=0.95,
                        reason=f"Matched explanation pattern: {pat.pattern!r}",
                    )
                if re.search(r"\b(calculate|compute|evaluate|work\s+out|solve)\b", stripped, re.I):
                    break
                return Intent(
                    type=EXPLANATION,
                    confidence=0.88,
                    reason="Conceptual phrasing dominates numeric signal.",
                )

        # ------------------------------------------------------------------
        # Gate 2 — CALCULATION
        # ------------------------------------------------------------------
        calc_hits = sum(1 for p in _CALCULATION_PATTERNS if p.search(stripped))
        if calc_hits >= 1:
            confidence = min(0.70 + calc_hits * 0.08, 0.98)
            return Intent(
                type=CALCULATION,
                confidence=confidence,
                reason=f"Matched {calc_hits} calculation pattern(s).",
            )

        # ------------------------------------------------------------------
        # Gate 3 — SEARCH via explicit verb (before datetime)
        # Fix 2: "Search for Bitcoin price today" must hit here, not datetime.
        # ------------------------------------------------------------------
        if _SEARCH_VERB_PATTERN.search(stripped):
            return Intent(type=SEARCH, confidence=0.92, reason="Explicit search verb matched.")

        # ------------------------------------------------------------------
        # Gate 4 — DATETIME
        # Strong patterns first; weak "today" only when no search verb present.
        # ------------------------------------------------------------------
        if any(p.search(stripped) for p in _DATETIME_STRONG_PATTERNS):
            return Intent(type=DATETIME, confidence=0.92, reason="Datetime pattern matched.")

        # Weak: bare "today" — safe here because search verb already handled above
        if _DATETIME_WEAK_TODAY.search(stripped):
            return Intent(type=DATETIME, confidence=0.80, reason="Bare 'today' matched.")

        # ------------------------------------------------------------------
        # Gate 5 — WEATHER
        # ------------------------------------------------------------------
        if any(p.search(stripped) for p in _WEATHER_PATTERNS):
            return Intent(type=WEATHER, confidence=0.92, reason="Weather pattern matched.")

        # ------------------------------------------------------------------
        # Gate 6 — SEARCH via recency/news nouns
        # Fix 1: "Latest AI news" — recency word + up to 40 chars + news noun
        # ------------------------------------------------------------------
        if any(p.search(stripped) for p in _SEARCH_PATTERNS):
            return Intent(type=SEARCH, confidence=0.88, reason="Search pattern matched.")

        # ------------------------------------------------------------------
        # Gates 7-9 — Domain tools
        # ------------------------------------------------------------------
        if any(p.search(stripped) for p in _FILE_PATTERNS):
            return Intent(type=FILE, confidence=0.88, reason="File pattern matched.")

        if any(p.search(stripped) for p in _PASSWORD_PATTERNS):
            return Intent(type=PASSWORD, confidence=0.92, reason="Password pattern matched.")

        if any(p.search(stripped) for p in _SYSTEM_PATTERNS):
            return Intent(type=SYSTEM, confidence=0.88, reason="System info pattern matched.")

        # ------------------------------------------------------------------
        # Gate 10 — GENERAL fallback
        # ------------------------------------------------------------------
        return Intent(type=GENERAL, confidence=0.60, reason="No specific pattern matched.")


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------

_default_classifier = IntentClassifier()


def classify_intent(text: str) -> Intent:
    """
    Classify the intent of a user message.

    Args:
        text: Raw user input.

    Returns:
        Intent(type, confidence, reason)

    Example:
        >>> classify_intent("What is the formula for percentage?")
        Intent(type='EXPLANATION', confidence=0.95)
        >>> classify_intent("15% of 340")
        Intent(type='CALCULATION', confidence=0.78)
        >>> classify_intent("Latest AI news")
        Intent(type='SEARCH', confidence=0.88)
        >>> classify_intent("Search for Bitcoin price today")
        Intent(type='SEARCH', confidence=0.92)
    """
    return _default_classifier.classify(text)
