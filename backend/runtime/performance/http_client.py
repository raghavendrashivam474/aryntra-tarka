"""
runtime/performance/http_client.py

Layer 2 — Shared async HTTP client for the Aryntra Tarka runtime.

Every plugin that performs external HTTP communication should route
requests through this module instead of instantiating its own httpx client.

Responsibilities:
    - Single shared AsyncClient across all plugins.
    - Connection pooling via httpx Limits.
    - HTTP/2 multiplexing.
    - Centralised timeout configuration.
    - Retry with exponential backoff.
    - Optional metrics hook per request.

Plugins never import httpx directly.
All HTTP mechanics live here.
"""

from __future__ import annotations

import asyncio
import time
import logging
from typing import Any, Callable, Optional

import httpx

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT = 10.0
MAX_CONNECTIONS = 100
MAX_KEEPALIVE = 20
RETRY_ATTEMPTS = 3
RETRY_BACKOFF = 0.5


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

# metrics_hook(url, duration_seconds, http_status_code)
MetricsHook = Optional[Callable[[str, float, int], None]]


# ---------------------------------------------------------------------------
# Shared Client
# ---------------------------------------------------------------------------

class RuntimeHttpClient:
    """
    Singleton async HTTP client shared across the entire runtime.

    Initialised once on startup and closed on shutdown via the
    FastAPI lifespan hook in main.py.

    Plugins never instantiate this directly.
    They call the module-level request() function instead.
    """

    _client: Optional[httpx.AsyncClient] = None

    @classmethod
    def get_client(cls) -> httpx.AsyncClient:
        """
        Return the shared AsyncClient, creating it on first call.

        Connection pool and HTTP/2 settings are applied once here
        and inherited by every request across all plugins.
        """
        if cls._client is None:
            cls._client = httpx.AsyncClient(
                timeout=httpx.Timeout(DEFAULT_TIMEOUT),
                limits=httpx.Limits(
                    max_connections=MAX_CONNECTIONS,
                    max_keepalive_connections=MAX_KEEPALIVE,
                ),
                http2=True,
            )
            log.debug(
                "RuntimeHttpClient initialised. "
                "max_connections=%d keepalive=%d timeout=%.1fs",
                MAX_CONNECTIONS,
                MAX_KEEPALIVE,
                DEFAULT_TIMEOUT,
            )
        return cls._client

    @classmethod
    async def close(cls) -> None:
        """
        Close the shared client and release all connections.

        Called once on application shutdown via the lifespan hook.
        """
        if cls._client is not None:
            await cls._client.aclose()
            cls._client = None
            log.debug("RuntimeHttpClient closed.")


# ---------------------------------------------------------------------------
# Request Wrapper
# ---------------------------------------------------------------------------

async def request(
    method: str,
    url: str,
    *,
    metrics_hook: MetricsHook = None,
    retry_attempts: int = RETRY_ATTEMPTS,
    retry_backoff: float = RETRY_BACKOFF,
    **kwargs: Any,
) -> httpx.Response:
    """
    Execute an HTTP request via the shared runtime client.

    Wraps the shared AsyncClient with:
        - Automatic retry with exponential backoff.
        - Optional metrics hook called on every successful response.
        - Structured logging on retry and failure.

    Parameters
    ----------
    method:
        HTTP method string e.g. "GET", "POST".
    url:
        Full URL of the endpoint.
    metrics_hook:
        Optional callable(url, duration_seconds, status_code).
        Called after every successful response.
    retry_attempts:
        Maximum number of attempts before raising.
        Defaults to RETRY_ATTEMPTS.
    retry_backoff:
        Base backoff seconds between retries.
        Actual wait = backoff * attempt_number.
    **kwargs:
        Forwarded directly to httpx.AsyncClient.request().
        Supports params, headers, json, timeout, etc.

    Returns
    -------
    httpx.Response
        The successful response object.

    Raises
    ------
    httpx.HTTPStatusError
        Raised by raise_for_status() on non-2xx responses.
    httpx.HTTPError
        Any transport-level failure after all retries exhausted.
    """
    client = RuntimeHttpClient.get_client()
    attempt = 0
    last_exception: Optional[Exception] = None

    while attempt < retry_attempts:
        try:
            start = time.perf_counter()
            response = await client.request(method, url, **kwargs)
            duration = time.perf_counter() - start

            if metrics_hook:
                metrics_hook(url, duration, response.status_code)

            log.debug(
                "[HTTP] %s %s → %d (%.3fs)",
                method,
                url,
                response.status_code,
                duration,
            )

            response.raise_for_status()
            return response

        except Exception as exc:
            attempt += 1
            last_exception = exc

            if attempt >= retry_attempts:
                log.error(
                    "[HTTP] %s %s failed after %d attempts: %s",
                    method,
                    url,
                    retry_attempts,
                    exc,
                )
                break

            wait = retry_backoff * attempt
            log.warning(
                "[HTTP] %s %s attempt %d failed. Retrying in %.1fs. Error: %s",
                method,
                url,
                attempt,
                wait,
                exc,
            )
            await asyncio.sleep(wait)

    raise last_exception  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------

async def get(
    url: str,
    *,
    metrics_hook: MetricsHook = None,
    **kwargs: Any,
) -> httpx.Response:
    """Shorthand for request("GET", url, ...)."""
    return await request("GET", url, metrics_hook=metrics_hook, **kwargs)


async def post(
    url: str,
    *,
    metrics_hook: MetricsHook = None,
    **kwargs: Any,
) -> httpx.Response:
    """Shorthand for request("POST", url, ...)."""
    return await request("POST", url, metrics_hook=metrics_hook, **kwargs)