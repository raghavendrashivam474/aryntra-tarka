# coding: utf-8
"""
plugins/weather/location_resolver.py

LocationResolver - Intelligent location resolution for the Weather Plugin.

Sprint v1.5.2 -> v1.6.0 (Integration Framework Migration)

Changes from v1.5.2:
    - _geocode() now uses OpenMeteoGeocodingProvider via the
      integration framework instead of raw httpx calls.
    - All normalization, scoring, and suggestion logic is unchanged.
    - Public interface is unchanged.
    - tool.py requires zero modifications.
"""

import re
import math
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from backend.runtime.integrations import (
    IntegrationClient,
    IntegrationError,
    execute_with_retry,
)
from backend.plugins.weather.providers import OpenMeteoGeocodingProvider

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_CANDIDATES = 10

_FILLER_WORDS = [
    r"\bweather\b",
    r"\bforecast\b",
    r"\btemperature\b",
    r"\btemp\b",
    r"\bcurrent\b",
    r"\btoday\b",
    r"\btomorrow\b",
    r"\bnow\b",
    r"\bhow'?s\b",
    r"\bhow\b",
    r"\bwhat'?s\b",
    r"\bwhat\b",
    r"\bthe\b",
    r"\bin\b",
    r"\bat\b",
    r"\bof\b",
    r"\bfor\b",
    r"\blike\b",
    r"\bis\b",
    r"\bit\b",
    r"\bwill\b",
    r"\bbe\b",
    r"\bdo\b",
    r"\bdoes\b",
    r"\btell\b",
    r"\bme\b",
    r"\bget\b",
    r"\bshow\b",
    r"\bgive\b",
    r"\bcheck\b",
]

_FILLER_PATTERN = re.compile(
    "|".join(_FILLER_WORDS),
    flags=re.IGNORECASE,
)

# Scoring weights
_WEIGHT_EXACT_NAME    = 50
_WEIGHT_COUNTRY_HINT  = 30
_WEIGHT_ADMIN_HINT    = 20
_WEIGHT_POPULATION    = 15
_WEIGHT_FIRST_RESULT  = 5

# Penalty when qualifier is present but candidate does not match it
_PENALTY_QUALIFIER_MISS = 25

# Minimum confidence to accept a result
_CONFIDENCE_THRESHOLD = 0.10


# ---------------------------------------------------------------------------
# Public result types
# ---------------------------------------------------------------------------

class ResolvedLocation:
    """
    Returned by LocationResolver.resolve() on success.

    Attributes:
        city        - Canonical city name from geocoding provider
        country     - Country name
        admin       - Administrative region (state / province), may be empty
        latitude    - WGS84 latitude
        longitude   - WGS84 longitude
        confidence  - Score in [0.0, 1.0] indicating match quality
        provider    - Always "Open-Meteo"
        timestamp   - ISO 8601 UTC string at resolution time
    """

    def __init__(
        self,
        city:       str,
        country:    str,
        admin:      str,
        latitude:   float,
        longitude:  float,
        confidence: float,
    ):
        self.city       = city
        self.country    = country
        self.admin      = admin
        self.latitude   = latitude
        self.longitude  = longitude
        self.confidence = round(confidence, 4)
        self.provider   = "Open-Meteo"
        self.timestamp  = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "city":       self.city,
            "country":    self.country,
            "admin":      self.admin,
            "latitude":   self.latitude,
            "longitude":  self.longitude,
            "confidence": self.confidence,
            "provider":   self.provider,
            "timestamp":  self.timestamp,
        }


class LocationNotFoundError(Exception):
    """
    Raised when no suitable location match is found.

    Attributes:
        query       - normalized query that was searched
        suggestions - list of candidate dicts (may be empty)
    """

    def __init__(self, query: str, suggestions: Optional[List[Dict]] = None):
        self.query       = query
        self.suggestions = suggestions or []
        super().__init__(f"Location not found: '{query}'")


class LocationNetworkError(Exception):
    """Raised on HTTP or connectivity failure during geocoding."""


# ---------------------------------------------------------------------------
# Provider instance (module-level singleton)
# ---------------------------------------------------------------------------

_geocoding_provider = OpenMeteoGeocodingProvider()


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------

class LocationResolver:
    """
    Resolves a raw location string into structured geographic metadata.

    Usage:
        resolver = LocationResolver()
        result   = resolver.resolve("weather in Delhi, India")
        # result.city       -> "Delhi"
        # result.country    -> "India"
        # result.latitude   -> 28.6519
        # result.longitude  -> 77.2315
        # result.confidence -> 0.96
    """

    def resolve(self, raw_input: str) -> ResolvedLocation:
        """
        Main entry point.

        Args:
            raw_input - raw string from user or planner

        Returns:
            ResolvedLocation

        Raises:
            LocationNotFoundError  - no match found or confidence too low
            LocationNetworkError   - network failure during geocoding
        """
        normalized, qualifier = self._normalize(raw_input)

        if not normalized:
            raise LocationNotFoundError(
                query="(empty)",
                suggestions=[],
            )

        # For geocoding API filtering, only pass qualifier if it is a
        # 2-letter ISO country code. Full words are evaluated at scoring time.
        api_country_code = qualifier if (qualifier and re.match(r"^[A-Z]{2}$", qualifier)) else ""

        candidates = self._geocode(normalized, api_country_code)

        if not candidates:
            raise LocationNotFoundError(
                query=normalized,
                suggestions=[],
            )

        scored = self._score_candidates(
            candidates = candidates,
            query      = normalized,
            qualifier  = qualifier,
        )

        best_score, best = scored[0]

        max_possible = (
            _WEIGHT_EXACT_NAME   +
            _WEIGHT_COUNTRY_HINT +
            _WEIGHT_ADMIN_HINT   +
            _WEIGHT_POPULATION   +
            _WEIGHT_FIRST_RESULT
        )
        confidence = min(best_score / max_possible, 1.0)

        if confidence < _CONFIDENCE_THRESHOLD:
            suggestions = self._format_suggestions(scored[:3])
            raise LocationNotFoundError(
                query       = normalized,
                suggestions = suggestions,
            )

        return ResolvedLocation(
            city       = best.get("name", normalized),
            country    = best.get("country", ""),
            admin      = best.get("admin1", ""),
            latitude   = best["latitude"],
            longitude  = best["longitude"],
            confidence = confidence,
        )

    # ------------------------------------------------------------------
    # Private - Normalization (unchanged)
    # ------------------------------------------------------------------

    def _normalize(self, raw: str) -> Tuple[str, str]:
        """
        Cleans raw user input and extracts a single optional qualifier.

        The qualifier is whatever comes after the first comma, or the
        second token if two tokens remain after filler stripping.

        Returns:
            (normalized_query, qualifier)
            qualifier is "" when not present.
        """
        text = raw.strip()

        if not text:
            return ("", "")

        qualifier = ""

        # Step 1 - Extract comma-separated qualifier
        parts = [p.strip() for p in text.split(",")]
        if len(parts) >= 2:
            qualifier = parts[-1].strip()
            text      = parts[0].strip()

        # Step 2 - Strip filler words from the location portion
        text = _FILLER_PATTERN.sub(" ", text)
        text = re.sub(r"\s+", " ", text).strip()

        # Step 3 - If two tokens remain and no qualifier yet,
        # treat second token as qualifier (e.g. "Paris Texas")
        if not qualifier:
            tokens = text.split()
            if len(tokens) == 2:
                qualifier = tokens[1]
                text      = tokens[0]

        # Normalize qualifier casing for 2-letter codes
        if qualifier and re.match(r"^[A-Za-z]{2}$", qualifier):
            qualifier = qualifier.upper()

        return (text, qualifier)

    # ------------------------------------------------------------------
    # Private - Geocoding (migrated to integration framework)
    # ------------------------------------------------------------------

    def _geocode(
        self,
        query:            str,
        api_country_code: str,
    ) -> List[Dict]:
        """
        Fetches geocoding results via OpenMeteoGeocodingProvider.

        Uses the integration framework for HTTP communication, timeouts,
        retries, logging, and error mapping.

        Returns list of raw result dicts.
        Raises LocationNetworkError on connectivity failure.
        """
        try:
            data = asyncio.run(
                self._geocode_async(query, api_country_code)
            )
        except IntegrationError as exc:
            raise LocationNetworkError(str(exc)) from exc

        return data.get("results") or []

    async def _geocode_async(
        self,
        query: str,
        api_country_code: str,
    ) -> Dict[str, Any]:
        """
        Async implementation that uses the integration framework.
        Called by _geocode() via asyncio.run().
        """
        async with IntegrationClient() as client:
            return await execute_with_retry(
                operation=lambda: _geocoding_provider.fetch(
                    client,
                    query=query,
                    country_code=api_country_code,
                ),
                policy=_geocoding_provider.retry_policy,
                provider=_geocoding_provider.name,
                operation_name="geocode",
            )

    # ------------------------------------------------------------------
    # Private - Scoring (unchanged)
    # ------------------------------------------------------------------

    def _score_candidates(
        self,
        candidates: List[Dict],
        query:      str,
        qualifier:  str,
    ) -> List[Tuple[float, Dict]]:
        """
        Scores each geocoding candidate and returns them sorted
        descending by score.
        """
        scored = []

        for idx, candidate in enumerate(candidates):
            score = 0.0

            candidate_name    = (candidate.get("name")         or "").strip()
            candidate_country = (candidate.get("country")      or "").strip()
            candidate_code    = (candidate.get("country_code") or "").upper().strip()
            candidate_admin   = (candidate.get("admin1")       or "").strip()
            population        = candidate.get("population") or 0

            # Exact name match
            if candidate_name.lower() == query.lower():
                score += _WEIGHT_EXACT_NAME

            # Qualifier matching
            if qualifier:
                q_lower = qualifier.lower()
                q_upper = qualifier.upper()

                country_match = (
                    q_upper == candidate_code or
                    q_lower == candidate_country.lower()
                )
                admin_match = (
                    q_lower in candidate_admin.lower() or
                    candidate_admin.lower() in q_lower
                )

                if country_match:
                    score += _WEIGHT_COUNTRY_HINT
                elif admin_match:
                    score += _WEIGHT_ADMIN_HINT
                else:
                    score -= _PENALTY_QUALIFIER_MISS

            # Population bonus (logarithmic scale)
            if population and population > 0:
                pop_score = min(math.log10(population) / 6.0, 1.0)
                score += _WEIGHT_POPULATION * pop_score

            # Positional bonus
            if idx == 0:
                score += _WEIGHT_FIRST_RESULT

            scored.append((score, candidate))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored

    # ------------------------------------------------------------------
    # Private - Suggestion formatting (unchanged)
    # ------------------------------------------------------------------

    def _format_suggestions(
        self,
        scored: List[Tuple[float, Dict]],
    ) -> List[Dict]:
        """
        Formats the top scored candidates into suggestion dicts.
        Used in LocationNotFoundError for did-you-mean responses.
        """
        suggestions = []
        for _score, candidate in scored:
            name    = candidate.get("name",    "")
            country = candidate.get("country", "")
            admin   = candidate.get("admin1",  "")

            label_parts = [name]
            if admin:
                label_parts.append(admin)
            if country:
                label_parts.append(country)

            suggestions.append({
                "name":    name,
                "country": country,
                "admin":   admin,
                "label":   ", ".join(label_parts),
            })

        return suggestions