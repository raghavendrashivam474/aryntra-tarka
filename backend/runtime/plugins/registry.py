# coding: utf-8
"""
runtime/plugins/registry.py

Layer 6 upgrade:
    PluginRegistry now delegates to PluginManager for lifecycle management.
    Existing API surface is preserved for backward compatibility.
"""

import logging
from typing import Any, Dict, List, Optional

from backend.runtime.plugins.base import PluginBase
from backend.runtime.plugins.manager import PluginManager

log = logging.getLogger(__name__)


class ToolRegistry:
    """
    Plugin registry — backward-compatible facade over PluginManager.

    Existing callers (bootstrap, tests) continue to work unchanged.
    Lifecycle management is delegated to PluginManager internally.
    """

    def __init__(self) -> None:
        self._manager = PluginManager()
        log.info("ToolRegistry initialised (Layer 6 — PluginManager backed)")

    @property
    def manager(self) -> PluginManager:
        """Expose PluginManager for bootstrap and inspection."""
        return self._manager

    def register(self, plugin: PluginBase) -> None:
        """
        Register a plugin instance directly.

        Backward-compatible path used by existing bootstrap code.
        Wraps the instance in a factory for PluginManager.
        """
        name    = plugin.name
        version = plugin.version

        # Wrap existing instance in a factory so PluginManager
        # can manage it without re-instantiation.
        instance = plugin

        def factory(inst=instance):
            return inst

        self._manager.register(
            name=name,
            version=version,
            factory=factory,
        )

    def unregister(self, name: str) -> None:
        """Unload and remove a plugin."""
        self._manager.unload(name)

    def find(self, name: str) -> Optional[PluginBase]:
        """Return the plugin instance, loading it if necessary."""
        return self._manager.get(name)

    def list(self) -> List[Dict]:
        """Return lifecycle metadata for all registered plugins."""
        return self._manager.list_all()

    def execute(self, name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a plugin by name."""
        plugin = self.find(name)
        if plugin is None:
            raise ValueError(f"Plugin not found or unavailable: {name}")
        log.info("Executing plugin: %s", name)
        self._manager.mark_busy(name)
        try:
            result = plugin.execute(input_data)
        finally:
            self._manager.mark_idle(name)
        return result