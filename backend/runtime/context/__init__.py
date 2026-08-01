"""
runtime/context

Layer 5 — Shared Context Framework.

Public surface for all plugins and runtime modules.

    from backend.runtime.context import SharedContext
    from backend.runtime.context import ResolvedLocation, ToolResult
    from backend.runtime.context import NS
"""

from .shared_context import SharedContext
from .entities import ResolvedLocation, ToolResult
from .namespaces import NS

__all__ = [
    "SharedContext",
    "ResolvedLocation",
    "ToolResult",
    "NS",
]