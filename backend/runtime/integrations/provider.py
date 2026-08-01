"""
integrations/provider.py

Abstract base class representing an external provider.

Every provider that the integration framework communicates with
implements ExternalProvider.

The hierarchy expected by the framework:

    ExternalProvider          (this module)
        OpenMeteoProvider     (weather integration)
        FutureSearchProvider  (future)
        FutureMapsProvider    (future)

Responsibilities of ExternalProvider
--------------------------------------
- Declare the provider name.
- Declare the base URL.
- Declare default timeout and retry policies.
- Implement fetch() to perform the actual provider call using the
  shared IntegrationClient.

The framework calls fetch() through execute_with_retry so providers
never implement retry loops themselves.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .client import IntegrationClient
from .retry import RetryPolicy, default_retry
from .timeout import TimeoutPolicy, default_timeout


class ExternalProvider(ABC):
    """
    Abstract base for all external integration providers.

    Subclasses must implement:
    - name       (property)   unique provider identifier
    - base_url   (property)   root URL of the external service
    - fetch()    (method)     perform the provider-specific request

    Subclasses may override:
    - timeout_policy    adjust per-provider timeout
    - retry_policy      adjust per-provider retry behaviour

    Usage inside a provider subclass
    ---------------------------------
    class OpenMeteoProvider(ExternalProvider):

        @property
        def name(self) -> str:
            return "open-meteo"

        @property
        def base_url(self) -> str:
            return "https://api.open-meteo.com"

        async def fetch(
            self,
            client: IntegrationClient,
            **kwargs: Any,
        ) -> Any:
            url = f"{self.base_url}/v1/forecast"
            return await client.get(
                url=url,
                params=kwargs,
                timeout=self.timeout_policy,
            )
    """

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique identifier for this provider.

        Used in log output, exception context, and ProviderMetadata.
        Examples: "open-meteo", "google-maps", "openai-search"
        """

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Root URL for the external service, without a trailing slash."""

    @abstractmethod
    async def fetch(
        self,
        client: IntegrationClient,
        **kwargs: Any,
    ) -> Any:
        """
        Perform the provider-specific request using the shared client.

        Parameters
        ----------
        client:
            The shared IntegrationClient already opened by the caller.
            Providers must NOT open or close the client themselves.
        **kwargs:
            Provider-specific parameters forwarded from the plugin.

        Returns
        -------
        Any
            Raw parsed response from the provider.
            The plugin layer is responsible for mapping this to a
            domain-specific data model.

        Raises
        ------
        IntegrationError subclasses
            Raised by IntegrationClient automatically.
            Providers do not need to catch or re-raise HTTP errors.
        """

    # ------------------------------------------------------------------
    # Overridable policy defaults
    # ------------------------------------------------------------------

    @property
    def timeout_policy(self) -> TimeoutPolicy:
        """
        Timeout configuration for this provider.

        Override in subclasses that communicate with slow or fast APIs.
        """
        return default_timeout()

    @property
    def retry_policy(self) -> RetryPolicy:
        """
        Retry configuration for this provider.

        Override in subclasses that require different retry behaviour.
        """
        return default_retry()

    # ------------------------------------------------------------------
    # Helpers available to subclasses
    # ------------------------------------------------------------------

    def endpoint(self, path: str) -> str:
        """
        Build a full URL from base_url and a relative path.

        Parameters
        ----------
        path:
            Relative path beginning with "/".

        Returns
        -------
        str
            Concatenated URL.

        Example
        -------
        self.endpoint("/v1/forecast")
        # -> "https://api.open-meteo.com/v1/forecast"
        """
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"