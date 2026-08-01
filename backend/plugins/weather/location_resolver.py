# coding: utf-8
"""
plugins/weather/location_resolver.py

LocationResolver - Intelligent location resolution for the Weather Plugin.

Layer 3 upgrade:
    resolve() and _geocode() are now fully async.
    asyncio.run() removed entirely.
    Cache is handled inside OpenMeteoGeocodingProvider transparently.
"""

import re
import math
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

_PENALTY_QUALIFIER_MISS = 25
_CONFIDENCE_THRESHOLD   = 0.10


# ---------------------------------------------------------------------------
# Public result types
# ---------------------------------------------------------------------------

class ResolvedLocation:
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
    def __init__(self, query: str, suggestions: Optional[List[Dict]] = None):
        self.query       = query
        self.suggestions = suggestions or []
        super().__init__(f"Location not found: '{query}'")


class LocationNetworkError(Exception):
    """Raised on HTTP or connectivity failure during geocoding."""


# ---------------------------------------------------------------------------
# Provider instance
# ---------------------------------------------------------------------------

_geocoding_provider = OpenMeteoGeocodingProvider()


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------

class LocationResolver:

    async def resolve(self, raw_input: str) -> ResolvedLocation:
        """
        Main entry point. Now fully async.

        Raises:
            LocationNotFoundError  - no match found or confidence too low
            LocationNetworkError   - network failure during geocoding
        """
        normalized, qualifier = self._normalize(raw_input)

        if not normalized:
            raise LocationNotFoundError(query="(empty)", suggestions=[])

        api_country_code = (
            qualifier
            if (qualifier and re.match(r"^[A-Z]{2}$", qualifier))
            else ""
        )

        candidates = await self._geocode(normalized, api_country_code)

        if not candidates:
            raise LocationNotFoundError(query=normalized, suggestions=[])

        scored = self._score_candidates(
            candidates=candidates,
            query=normalized,
            qualifier=qualifier,
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
                query=normalized,
                suggestions=suggestions,
            )

        return ResolvedLocation(
            city=best.get("name", normalized),
            country=best.get("country", ""),
            admin=best.get("admin1", ""),
            latitude=best["latitude"],
            longitude=best["longitude"],
            confidence=confidence,
        )

    # ------------------------------------------------------------------
    # Private - Normalization
    # ------------------------------------------------------------------

    def _normalize(self, raw: str) -> Tuple[str, str]:
        text = raw.strip()
        if not text:
            return ("", "")

        qualifier = ""

        parts = [p.strip() for p in text.split(",")]
        if len(parts) >= 2:
            qualifier = parts[-1].strip()
            text      = parts[0].strip()

        text = _FILLER_PATTERN.sub(" ", text)
        text = re.sub(r"\s+", " ", text).strip()

        if not qualifier:
            tokens = text.split()
            if len(tokens) == 2:
                qualifier = tokens[1]
                text      = tokens[0]

        if qualifier and re.match(r"^[A-Za-z]{2}$", qualifier):
            qualifier = qualifier.upper()

        return (text, qualifier)

    # ------------------------------------------------------------------
    # Private - Geocoding (fully async)
    # ------------------------------------------------------------------

    async def _geocode(
        self,
        query:            str,
        api_country_code: str,
    ) -> List[Dict]:
        """
        Fetches geocoding results via OpenMeteoGeocodingProvider.
        Fully async. No asyncio.run().
        Cache handled inside the provider transparently.
        """
        try:
            async with IntegrationClient() as client:
                data = await execute_with_retry(
                    operation=lambda: _geocoding_provider.fetch(
                        client,
                        query=query,
                        country_code=api_country_code,
                    ),
                    policy=_geocoding_provider.retry_policy,
                    provider=_geocoding_provider.name,
                    operation_name="geocode",
                )
        except IntegrationError as exc:
            raise LocationNetworkError(str(exc)) from exc

        return data.get("results") or []

    # ------------------------------------------------------------------
    # Private - Scoring
    # ------------------------------------------------------------------

    def _score_candidates(
        self,
        candidates: List[Dict],
        query:      str,
        qualifier:  str,
    ) -> List[Tuple[float, Dict]]:
        scored = []

        for idx, candidate in enumerate(candidates):
            score = 0.0

            candidate_name    = (candidate.get("name")         or "").strip()
            candidate_country = (candidate.get("country")      or "").strip()
            candidate_code    = (candidate.get("country_code") or "").upper().strip()
            candidate_admin   = (candidate.get("admin1")       or "").strip()
            population        = candidate.get("population") or 0

            if candidate_name.lower() == query.lower():
                score += _WEIGHT_EXACT_NAME

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

            if population and population > 0:
                pop_score = min(math.log10(population) / 6.0, 1.0)
                score += _WEIGHT_POPULATION * pop_score

            if idx == 0:
                score += _WEIGHT_FIRST_RESULT

            scored.append((score, candidate))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored

    # ------------------------------------------------------------------
    # Private - Suggestion formatting
    # ------------------------------------------------------------------

    def _format_suggestions(
        self,
        scored: List[Tuple[float, Dict]],
    ) -> List[Dict]:
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