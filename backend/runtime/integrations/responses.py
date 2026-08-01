"""
integrations/responses.py

Shared response models for all external integration plugins.

Every plugin that uses the integration framework returns its result
wrapped in one of these models.  This ensures a consistent envelope
across all providers while still allowing plugin-specific payloads.

Models
------
ProviderMetadata    Diagnostic metadata about the provider call.
SuccessResponse     Wraps a successful provider result.
ErrorResponse       Wraps a failed provider result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

# Type variable for the plugin-specific payload inside SuccessResponse.
T = TypeVar("T")


# ---------------------------------------------------------------------------
# ProviderMetadata
# ---------------------------------------------------------------------------

@dataclass
class ProviderMetadata:
    """
    Diagnostic metadata attached to every integration response.

    Attributes
    ----------
    provider:
        Identifier for the external provider (e.g. "open-meteo").
    endpoint:
        The URL or logical endpoint that was called.
    duration_ms:
        Total round-trip time in milliseconds.
    attempts:
        Number of attempts made including the successful one.
    retrieved_at:
        UTC timestamp recorded immediately after the response arrived.
    """

    provider:     str
    endpoint:     str
    duration_ms:  float
    attempts:     int                    = 1
    retrieved_at: datetime               = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider":     self.provider,
            "endpoint":     self.endpoint,
            "duration_ms":  round(self.duration_ms, 2),
            "attempts":     self.attempts,
            "retrieved_at": self.retrieved_at.isoformat(),
        }


# ---------------------------------------------------------------------------
# SuccessResponse
# ---------------------------------------------------------------------------

@dataclass
class SuccessResponse(Generic[T]):
    """
    Standard envelope for a successful external provider call.

    Attributes
    ----------
    data:
        The plugin-specific payload.  Type is determined by the plugin.
    metadata:
        Diagnostic information about the provider call.

    Usage
    -----
    result: SuccessResponse[WeatherData] = SuccessResponse(
        data=weather_data,
        metadata=provider_metadata,
    )
    """

    data:     T
    metadata: ProviderMetadata

    @property
    def ok(self) -> bool:
        return True

    def as_dict(self) -> dict[str, Any]:
        payload = (
            self.data.as_dict()
            if hasattr(self.data, "as_dict")
            else self.data
        )
        return {
            "ok":       True,
            "data":     payload,
            "metadata": self.metadata.as_dict(),
        }


# ---------------------------------------------------------------------------
# ErrorResponse
# ---------------------------------------------------------------------------

@dataclass
class ErrorResponse:
    """
    Standard envelope for a failed external provider call.

    Attributes
    ----------
    error_code:
        Machine-readable code identifying the failure category.
        Examples: "network_error", "timeout", "provider_unavailable",
                  "invalid_response", "retry_exhausted"
    error_message:
        Human-readable description of the failure.
    metadata:
        Diagnostic information, as available at the point of failure.
    recoverable:
        True when the caller may reasonably retry the operation later.

    Usage
    -----
    result: ErrorResponse = ErrorResponse(
        error_code="provider_unavailable",
        error_message="Open-Meteo returned HTTP 503",
        metadata=provider_metadata,
        recoverable=True,
    )
    """

    error_code:    str
    error_message: str
    metadata:      ProviderMetadata
    recoverable:   bool = False

    @property
    def ok(self) -> bool:
        return False

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok":            False,
            "error_code":    self.error_code,
            "error_message": self.error_message,
            "recoverable":   self.recoverable,
            "metadata":      self.metadata.as_dict(),
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def error_code_for(exception: Exception) -> str:
    """
    Map an IntegrationError subclass to a standard error_code string.

    Falls back to "integration_error" for unrecognised exception types.
    """
    # Import here to avoid circular dependency at module load time.
    from .exceptions import (
        IntegrationTimeoutError,
        InvalidResponse,
        NetworkError,
        ProviderUnavailable,
        RetryExhausted,
    )

    mapping = {
        NetworkError:              "network_error",
        IntegrationTimeoutError:   "timeout",
        ProviderUnavailable:       "provider_unavailable",
        InvalidResponse:           "invalid_response",
        RetryExhausted:            "retry_exhausted",
    }
    return mapping.get(type(exception), "integration_error")
