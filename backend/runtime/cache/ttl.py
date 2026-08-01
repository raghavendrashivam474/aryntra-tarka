"""
runtime/cache/ttl.py

Centralised TTL configuration for all cache namespaces.

The runtime owns TTL definitions.
Plugins do not define their own expiration logic.

Each constant represents a deliberate freshness policy
for a specific type of resource.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# TTL Constants (seconds)
# ---------------------------------------------------------------------------

# Geocoding results — city coordinates are effectively static.
# 7 days is safe. Future plugins (Maps, Places, Travel) share this.
GEOCODING_TTL: int = 60 * 60 * 24 * 7   # 7 days

# Weather conditions — time-sensitive. Fresh enough for current conditions.
WEATHER_TTL: int = 60 * 10              # 10 minutes

# Generic short-lived responses (search results, news headlines).
SHORT_TTL: int = 60 * 5                 # 5 minutes

# Generic medium-lived responses (provider metadata, config).
MEDIUM_TTL: int = 60 * 60              # 1 hour

# Generic long-lived responses (reference data, static lookups).
LONG_TTL: int = 60 * 60 * 24          # 24 hours