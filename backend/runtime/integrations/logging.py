"""
integrations/logging.py

Structured request logging for all external integration plugins.

Every integration call is bracketed by a log entry at start and a log
entry at completion.  Plugins do not implement logging themselves.

Usage
-----
async with log_integration_call(provider="open-meteo", endpoint=url) as ctx:
    response = await http_client.get(url)
    ctx.record_attempts(attempts)

The context manager records duration automatically and emits the
completion log when the block exits.
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import AsyncIterator

log = logging.getLogger("aryntra.integrations")


# ---------------------------------------------------------------------------
# CallContext
# ---------------------------------------------------------------------------

@dataclass
class CallContext:
    """
    Mutable context object available inside a log_integration_call block.

    The caller uses this to report the final attempt count after retries
    have resolved.  The context manager reads it when emitting the
    completion log.
    """

    provider:     str
    endpoint:     str
    _attempts:    int   = field(default=1,   init=False, repr=False)
    _start:       float = field(default=0.0, init=False, repr=False)

    def record_attempts(self, attempts: int) -> None:
        """Record how many attempts were required."""
        self._attempts = attempts

    @property
    def attempts(self) -> int:
        return self._attempts

    @property
    def elapsed_ms(self) -> float:
        """Milliseconds elapsed since the context was entered."""
        return (time.perf_counter() - self._start) * 1_000


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------

@asynccontextmanager
async def log_integration_call(
    provider: str,
    endpoint: str,
) -> AsyncIterator[CallContext]:
    """
    Async context manager that logs the start and outcome of an integration
    call and measures its duration.

    Parameters
    ----------
    provider:
        Human-readable provider identifier (e.g. "open-meteo").
    endpoint:
        The URL or logical name of the endpoint being called.

    Yields
    ------
    CallContext
        Mutable context that the caller can update before the block exits.

    On success
    ----------
    Emits an INFO log with provider, endpoint, duration, and attempt count.

    On failure
    ----------
    Emits a WARNING log with the same fields plus the exception message,
    then re-raises the exception.

    Example
    -------
    async with log_integration_call("open-meteo", url) as ctx:
        data = await _fetch(url)
        ctx.record_attempts(2)
    """
    ctx = CallContext(provider=provider, endpoint=endpoint)
    ctx._start = time.perf_counter()

    log.debug(
        "Integration call started | provider=%s endpoint=%s",
        provider,
        endpoint,
    )

    try:
        yield ctx

    except Exception as exc:
        elapsed = ctx.elapsed_ms
        log.warning(
            "Integration call failed  | provider=%s endpoint=%s "
            "duration_ms=%.1f attempts=%d error=%s",
            provider,
            endpoint,
            elapsed,
            ctx.attempts,
            exc,
        )
        raise

    else:
        elapsed = ctx.elapsed_ms
        log.info(
            "Integration call success | provider=%s endpoint=%s "
            "duration_ms=%.1f attempts=%d",
            provider,
            endpoint,
            elapsed,
            ctx.attempts,
        )


# ---------------------------------------------------------------------------
# Standalone helpers
# ---------------------------------------------------------------------------

def log_retry_attempt(
    provider: str,
    attempt: int,
    max_attempts: int,
    reason: str,
) -> None:
    """Emit a structured warning when a retry is about to be attempted."""
    log.warning(
        "Retrying | provider=%s attempt=%d/%d reason=%s",
        provider,
        attempt,
        max_attempts,
        reason,
    )


def log_retry_exhausted(
    provider: str,
    attempts: int,
) -> None:
    """Emit a structured error when all retry attempts are consumed."""
    log.error(
        "Retry exhausted | provider=%s total_attempts=%d",
        provider,
        attempts,
    )
