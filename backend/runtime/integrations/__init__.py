"""
runtime/integrations

Reusable framework for all external integration plugins.

Public surface
--------------
Plugins import from this package rather than from individual modules.

    from runtime.integrations import (
        ExternalProvider,
        IntegrationClient,
        RetryPolicy,
        TimeoutPolicy,
        SuccessResponse,
        ErrorResponse,
        ProviderMetadata,
        IntegrationError,
        NetworkError,
        IntegrationTimeoutError,
        ProviderUnavailable,
        InvalidResponse,
        RetryExhausted,
        log_integration_call,
        execute_with_retry,
        default_retry,
        no_retry,
        aggressive_retry,
        default_timeout,
        relaxed_timeout,
        strict_timeout,
        error_code_for,
    )
"""

from .client import IntegrationClient
from .exceptions import (
    IntegrationError,
    IntegrationTimeoutError,
    InvalidResponse,
    NetworkError,
    ProviderUnavailable,
    RetryExhausted,
)
from .logging import log_integration_call
from .provider import ExternalProvider
from .responses import ErrorResponse, ProviderMetadata, SuccessResponse, error_code_for
from .retry import (
    RetryPolicy,
    aggressive_retry,
    default_retry,
    execute_with_retry,
    no_retry,
)
from .timeout import (
    TimeoutPolicy,
    default_timeout,
    relaxed_timeout,
    strict_timeout,
)

__all__ = [
    # Client
    "IntegrationClient",
    # Provider base
    "ExternalProvider",
    # Retry
    "RetryPolicy",
    "execute_with_retry",
    "default_retry",
    "no_retry",
    "aggressive_retry",
    # Timeout
    "TimeoutPolicy",
    "default_timeout",
    "relaxed_timeout",
    "strict_timeout",
    # Responses
    "SuccessResponse",
    "ErrorResponse",
    "ProviderMetadata",
    "error_code_for",
    # Exceptions
    "IntegrationError",
    "NetworkError",
    "IntegrationTimeoutError",
    "ProviderUnavailable",
    "InvalidResponse",
    "RetryExhausted",
    # Logging
    "log_integration_call",
]
