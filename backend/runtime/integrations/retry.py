"""
integrations/retry.py

Centralised retry policy and execution engine for all external integrations.

Plugins declare a RetryPolicy rather than implementing their own backoff
loops.  The execute_with_retry function handles all retry mechanics so
plugin code stays focused on business logic.

Retry behaviour
---------------
- Retries are attempted only for status codes listed in retryable_status_codes
  or for transport-level errors (NetworkError, IntegrationTimeoutError).
- Delay between attempts grows exponentially: base * (2 ** attempt).
- Maximum delay is capped by max_delay_seconds to prevent excessively long
  waits on providers with high retry counts.
- ProviderUnavailable is raised for non-retryable HTTP errors immediately.
- RetryExhausted is raised when all attempts are consumed.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Awaitable, Callable, TypeVar

from .exceptions import (
    IntegrationError,
    IntegrationTimeoutError,
    NetworkError,
    RetryExhausted,
)

log = logging.getLogger(__name__)

T = TypeVar("T")

# ---------------------------------------------------------------------------
# Retryable HTTP status codes
# ---------------------------------------------------------------------------

DEFAULT_RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({
    429,  # Too Many Requests
    500,  # Internal Server Error
    502,  # Bad Gateway
    503,  # Service Unavailable
    504,  # Gateway Timeout
})


# ---------------------------------------------------------------------------
# RetryPolicy
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RetryPolicy:
    """
    Immutable retry configuration for a single integration.

    Attributes
    ----------
    max_attempts:
        Total number of attempts including the first.
        A value of 1 means no retries.
    base_delay_seconds:
        Initial wait time before the second attempt.
        Subsequent delays double each time (exponential backoff).
    max_delay_seconds:
        Upper bound on inter-attempt delay regardless of backoff growth.
    retryable_status_codes:
        HTTP status codes that should trigger a retry.
        Transport errors always trigger a retry regardless of this set.

    Usage
    -----
    policy = RetryPolicy()                             # platform defaults
    policy = RetryPolicy(max_attempts=5)               # more aggressive
    policy = RetryPolicy(max_attempts=1)               # disable retries
    """

    max_attempts:           int            = 3
    base_delay_seconds:     float          = 1.0
    max_delay_seconds:      float          = 30.0
    retryable_status_codes: frozenset[int] = field(
        default_factory=lambda: DEFAULT_RETRYABLE_STATUS_CODES
    )

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError(
                f"RetryPolicy.max_attempts must be >= 1, got {self.max_attempts}"
            )
        if self.base_delay_seconds < 0:
            raise ValueError(
                "RetryPolicy.base_delay_seconds must be non-negative"
            )

    def delay_for_attempt(self, attempt: int) -> float:
        """
        Return the delay in seconds before the given attempt number.

        Parameters
        ----------
        attempt:
            Zero-based attempt index.
            Attempt 0 is the first call; delay before attempt 0 is always 0.

        Returns
        -------
        float
            Seconds to wait.  Never exceeds max_delay_seconds.
        """
        if attempt == 0:
            return 0.0
        delay = self.base_delay_seconds * (2 ** (attempt - 1))
        return min(delay, self.max_delay_seconds)


# ---------------------------------------------------------------------------
# Execution engine
# ---------------------------------------------------------------------------

async def execute_with_retry(
    operation: Callable[[], Awaitable[T]],
    policy: RetryPolicy,
    provider: str = "unknown",
    operation_name: str = "request",
) -> T:
    """
    Execute an async operation with retry behaviour defined by policy.

    Parameters
    ----------
    operation:
        An async callable that performs the actual work.
        It should raise IntegrationError subclasses on failure.
    policy:
        The RetryPolicy governing how many retries to attempt.
    provider:
        Provider name used in log messages and exception context.
    operation_name:
        Human-readable label for the operation in log output.

    Returns
    -------
    T
        The result of the first successful call to operation().

    Raises
    ------
    RetryExhausted
        When all attempts are consumed without a successful result.
    IntegrationError
        For non-retryable failures.  Raised immediately without retry.
    """
    last_exception: Exception | None = None

    for attempt in range(policy.max_attempts):
        delay = policy.delay_for_attempt(attempt)

        if delay > 0:
            log.debug(
                "Retry delay before attempt %d/%d for %s.%s (%.1fs)",
                attempt + 1,
                policy.max_attempts,
                provider,
                operation_name,
                delay,
            )
            await asyncio.sleep(delay)

        try:
            log.debug(
                "Attempt %d/%d | %s.%s",
                attempt + 1,
                policy.max_attempts,
                provider,
                operation_name,
            )
            result = await operation()
            log.debug(
                "Attempt %d succeeded | %s.%s",
                attempt + 1,
                provider,
                operation_name,
            )
            return result

        except (NetworkError, IntegrationTimeoutError) as exc:
            # Transport-level errors are always retryable.
            log.warning(
                "Retryable transport error on attempt %d/%d | %s.%s: %s",
                attempt + 1,
                policy.max_attempts,
                provider,
                operation_name,
                exc,
            )
            last_exception = exc

        except IntegrationError:
            # Non-retryable integration errors bubble up immediately.
            raise

    raise RetryExhausted(
        message=(
            f"All {policy.max_attempts} attempt(s) failed for "
            f"{provider}.{operation_name}"
        ),
        provider=provider,
        attempts=policy.max_attempts,
        last_exception=last_exception,
    )


# ---------------------------------------------------------------------------
# Convenience constructors
# ---------------------------------------------------------------------------

def default_retry() -> RetryPolicy:
    """Return the platform-default RetryPolicy."""
    return RetryPolicy()


def no_retry() -> RetryPolicy:
    """Return a RetryPolicy that disables all retries."""
    return RetryPolicy(max_attempts=1)


def aggressive_retry() -> RetryPolicy:
    """Return a RetryPolicy with more attempts for unreliable providers."""
    return RetryPolicy(
        max_attempts=5,
        base_delay_seconds=2.0,
        max_delay_seconds=60.0,
    )