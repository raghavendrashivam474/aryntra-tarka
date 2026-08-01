"""
integrations/exceptions.py

Platform-standard exceptions for all external integration plugins.

Every exception raised by the integration framework maps to one of
these types.  Plugins receive structured exceptions rather than raw
HTTP library errors.

Hierarchy
---------
IntegrationError                   (base)
    NetworkError                   transport-level failure
    IntegrationTimeoutError        request exceeded time limit
    ProviderUnavailable            provider returned 5xx / unreachable
    InvalidResponse                response could not be parsed or was malformed
    RetryExhausted                 all retry attempts failed
"""


class IntegrationError(Exception):
    """
    Base class for all integration framework exceptions.

    All plugin-facing exceptions inherit from this type so callers
    can catch the broad category or a specific subclass.
    """

    def __init__(self, message: str, provider: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.provider = provider

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"provider={self.provider!r}, "
            f"message={self.message!r})"
        )


class NetworkError(IntegrationError):
    """
    Raised when a transport-level failure prevents the request
    from reaching the provider.

    Examples
    --------
    - DNS resolution failure
    - Connection refused
    - Socket closed unexpectedly
    """


class IntegrationTimeoutError(IntegrationError):
    """
    Raised when a request exceeds the configured timeout threshold.

    Named IntegrationTimeoutError to avoid shadowing the built-in
    TimeoutError while remaining descriptive at the call site.
    """

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        super().__init__(message, provider)
        self.timeout_seconds = timeout_seconds


class ProviderUnavailable(IntegrationError):
    """
    Raised when the provider is reachable but unable to serve
    the request successfully.

    Examples
    --------
    - HTTP 500 Internal Server Error
    - HTTP 502 Bad Gateway
    - HTTP 503 Service Unavailable
    - HTTP 429 Too Many Requests
    """

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message, provider)
        self.status_code = status_code


class InvalidResponse(IntegrationError):
    """
    Raised when the provider returns a response that cannot be
    parsed or does not match the expected structure.

    Examples
    --------
    - Response body is not valid JSON
    - Expected field is missing
    - Field contains an unexpected type
    """


class RetryExhausted(IntegrationError):
    """
    Raised when all retry attempts have been consumed and the
    request has still not succeeded.

    Wraps the last exception that caused the final attempt to fail.
    """

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        attempts: int = 0,
        last_exception: Exception | None = None,
    ) -> None:
        super().__init__(message, provider)
        self.attempts = attempts
        self.last_exception = last_exception
