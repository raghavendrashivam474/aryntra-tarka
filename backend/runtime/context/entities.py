"""
runtime/context/entities.py

Typed entity dataclasses for the SharedContext.

Entities represent structured resolved data that can be
shared across plugins within a single request.

Current entities:
    ResolvedLocation — geographic coordinates and metadata
    ToolResult       — structured output from a tool execution

Future entities:
    ResolvedTime     — parsed datetime with timezone
    ResolvedUser     — resolved user identity
    ResolvedRepo     — resolved code repository
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ResolvedLocation:
    """
    A resolved geographic location.

    Stored in SharedContext under namespace "location".
    Reusable by any plugin that needs coordinates within
    the same request — Maps, Weather, Places, Travel etc.

    Attributes
    ----------
    city:
        Canonical city name from geocoding provider.
    country:
        Country name.
    admin:
        Administrative region (state / province). May be empty.
    latitude:
        WGS84 latitude.
    longitude:
        WGS84 longitude.
    confidence:
        Match quality score in [0.0, 1.0].
    provider:
        Geocoding provider name.
    """

    city:       str
    country:    str
    latitude:   float
    longitude:  float
    admin:      str   = ""
    confidence: float = 0.0
    provider:   str   = "Open-Meteo"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "city":       self.city,
            "country":    self.country,
            "admin":      self.admin,
            "latitude":   self.latitude,
            "longitude":  self.longitude,
            "confidence": self.confidence,
            "provider":   self.provider,
        }


@dataclass
class ToolResult:
    """
    The structured output from a single tool execution.

    Stored in SharedContext under namespace "tool.{tool_name}".
    Allows downstream plugins to read the output of upstream tools
    within the same request without re-executing them.

    Attributes
    ----------
    tool_name:
        Name of the tool that produced this result.
    success:
        True if the tool completed without error.
    data:
        Full structured output dict.
    raw:
        Formatted string representation.
    error:
        Error message if success is False.
    """

    tool_name: str
    success:   bool
    data:      Dict[str, Any] = field(default_factory=dict)
    raw:       str            = ""
    error:     Optional[str]  = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "success":   self.success,
            "data":      self.data,
            "raw":       self.raw,
            "error":     self.error,
        }