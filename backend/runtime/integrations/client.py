"""
integrations/client.py

Shared async HTTP client for all external integration plugins.

Plugins never import httpx or requests directly.
All HTTP communication flows through IntegrationClient.

The client handles:
- GET and POST requests
- Query parameters and headers
- JSON parsing
- Timeout application
- Exception mapping (raw httpx errors -> IntegrationError subclasses)

Retry logic lives in retry.py and wraps this client at the provider
layer.  The client itself makes exactly one attempt per call.

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

    Plugins obtain an instance via the async context manager and call
    get() or post() to communicate with external providers.

    Example
    -------
    async with IntegrationClient(base_headers={"User-Agent": "Tarka/1.0"}) as c:
        payload = await c.get(url, params={"q": "London"})
    """

    def __init__(
        self,
        base_headers: dict[str, str] | None = None,
    ) -> None:
        self._base_headers: dict[str, str] = base_headers or {}
        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "IntegrationClient":
        self._client = httpx.AsyncClient(headers=self._base_headers)
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

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
        """Execute one HTTP request and map errors to IntegrationError types."""
        self._assert_open()

        httpx_timeout = httpx.Timeout(**timeout.as_httpx_timeout())

        try:
            response = await self._client.request(  # type: ignore[union-attr]
                method=method,
                url=url,
                params=params,
                headers=headers,
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

    def _assert_open(self) -> None:
        if self._client is None:
            raise RuntimeError(
                "IntegrationClient must be used as an async context manager. "
                "Use: async with IntegrationClient() as client: ..."
            )
