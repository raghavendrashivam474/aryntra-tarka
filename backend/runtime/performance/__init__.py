"""
runtime/performance

Layer 2 — Platform Performance Framework.

Public surface for all plugins and internal runtime modules.

    from backend.runtime.performance import get, post, request, RuntimeHttpClient
"""

from .http_client import (
    RuntimeHttpClient,
    get,
    post,
    request,
)

__all__ = [
    "RuntimeHttpClient",
    "request",
    "get",
    "post",
]