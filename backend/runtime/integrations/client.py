"""
integrations/client.py

Shared async HTTP client for all external integration plugins.

Layer 2 upgrade:
    The internal httpx.AsyncClient is now sourced from RuntimeHttpClient
    (runtime/performance/http_client.py) instead of being created per
    IntegrationClient instance.

    This means every plugin shares:
        - One connection pool.
        - HTTP/2 multiplexing.
        - Centralised timeout and retry defaults.

    The public API of IntegrationClient is completely unchanged.
    Existing providers require zero modification.

Plugins never import httpx or requests directly.
All HTTP communication flows through IntegrationClient.

The client handles:
    - GET and POST requests.
    - Query parameters and headers.
    - JSON parsing.
    - Timeout application.
    - Exception mapping (raw httpx errors -> IntegrationError subclasses).

Retry logic lives in retry.py and wraps this client at the provider layer.
The client itself makes exactly one attempt per call.

Usage
-----
async with IntegrationClient() as client:
    data = await client.get(
        url="https://api.example.com/data",
        params={"key": "value"},
        timeout=TimeoutPolicy(),
    )
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from backend.runtime.performance.http_client import RuntimeHttpClient

from .exceptions import (
    IntegrationTimeoutError,
    InvalidResponse,
    NetworkError,
    ProviderUnavailable,
)
from .timeout import TimeoutPolicy, default_timeout

log = logging.getLogger(__name__)


class IntegrationClient:
    """
    Async HTTP client providing a plugin-friendly interface over httpx.

    Layer 2: internally delegates to the shared RuntimeHttpClient rather
    than creating a new httpx.AsyncClient per instance.

    The context manager API is preserved for backward compatibility.
    Existing providers using:

        async with IntegrationClient() as client:
            data = await client.get(url, ...)

    require no changes.
    """

    def __init__(
        self,
        base_headers: dict[str, str] | None = None,
    ) -> None:
        self._base_headers: dict[str, str] = base_headers or {}

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "IntegrationClient":
        # No client creation needed.
        # The shared RuntimeHttpClient is already initialised.
        return self

    async def __aexit__(self, *_: Any) -> None:
        # No teardown needed.
        # The shared client lifecycle is managed by the lifespan hook.
        pass

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: TimeoutPolicy | None = None,
    ) -> Any:
        """
        Perform an HTTP GET request and return the parsed JSON body.

        Parameters
        ----------
        url:
            Full URL of the endpoint.
        params:
            Query string parameters.
        headers:
            Request-level headers merged with base_headers.
        timeout:
            Timeout policy for this request.
            Defaults to the platform default if omitted.

        Returns
        -------
        Any
            Parsed JSON payload (dict, list, or scalar).

        Raises
        ------
        NetworkError
            Transport-level failure.
        IntegrationTimeoutError
            Request exceeded the configured timeout.
        ProviderUnavailable
            Provider returned a non-2xx status code.
        InvalidResponse
            Response body could not be decoded as JSON.
        """
        return await self._request(
            method="GET",
            url=url,
            params=params,
            headers=headers,
            json_body=None,
            timeout=timeout or default_timeout(),
        )

    async def post(
        self,
        url: str,
        json_body: Any | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: TimeoutPolicy | None = None,
    ) -> Any:
        """
        Perform an HTTP POST request and return the parsed JSON body.

        Parameters
        ----------
        url:
            Full URL of the endpoint.
        json_body:
            Python object to serialise as the JSON request body.
        params:
            Query string parameters.
        headers:
            Request-level headers merged with base_headers.
        timeout:
            Timeout policy for this request.

        Returns
        -------
        Any
            Parsed JSON payload.

        Raises
        ------
        NetworkError, IntegrationTimeoutError, ProviderUnavailable,
        InvalidResponse
            Same semantics as get().
        """
        return await self._request(
            method="POST",
            url=url,
            params=params,
            headers=headers,
            json_body=json_body,
            timeout=timeout or default_timeout(),
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None,
        headers: dict[str, str] | None,
        json_body: Any | None,
        timeout: TimeoutPolicy,
    ) -> Any:
        """
        Execute one HTTP request via the shared RuntimeHttpClient
        and map errors to IntegrationError types.
        """
        client = RuntimeHttpClient.get_client()

        merged_headers = {**self._base_headers, **(headers or {})}
        httpx_timeout = httpx.Timeout(**timeout.as_httpx_timeout())

        try:
            response = await client.request(
                method=method,
                url=url,
                params=params,
                headers=merged_headers or None,
                json=json_body,
                timeout=httpx_timeout,
            )
        except httpx.TimeoutException as exc:
            raise IntegrationTimeoutError(
                message=f"Request timed out after {timeout.total_seconds}s: {exc}",
                timeout_seconds=timeout.total_seconds,
            ) from exc
        except httpx.NetworkError as exc:
            raise NetworkError(
                message=f"Network error during {method} {url}: {exc}"
            ) from exc
        except httpx.HTTPError as exc:
            raise NetworkError(
                message=f"HTTP transport error during {method} {url}: {exc}"
            ) from exc

        if not response.is_success:
            raise ProviderUnavailable(
                message=(
                    f"Provider returned HTTP {response.status_code} "
                    f"for {method} {url}"
                ),
                status_code=response.status_code,
            )

        try:
            return response.json()
        except Exception as exc:
            raise InvalidResponse(
                message=f"Response from {url} is not valid JSON: {exc}"
            ) from exc