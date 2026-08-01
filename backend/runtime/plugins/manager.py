# coding: utf-8
"""
runtime/plugins/manager.py

Layer 6 — PluginManager.

The runtime owns plugin instances.
Plugins own only their internal business logic and resources.

PluginManager is the single authority for:
    - Plugin registration (metadata only)
    - Lazy instantiation (on first use)
    - Lifecycle state tracking
    - Health monitoring
    - Resource cleanup

Plugins are never instantiated at bootstrap time.
They are instantiated on first request and kept alive
until explicitly unloaded or the process exits.

Usage
-----
manager = PluginManager()

# Register plugin class (no instantiation yet)
manager.register(name="weather", version="1.5.2", factory=WeatherPlugin)

# Get plugin instance (instantiates on first call)
plugin = manager.get("weather")

# Inspect state
state = manager.state("weather")

# Unload
manager.unload("weather")

# List all
records = manager.list_all()
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from backend.runtime.plugins.lifecycle import PluginLifecycle, PluginState

log = logging.getLogger(__name__)


class PluginManager:
    """
    Central plugin lifecycle manager.

    The runtime owns all PluginLifecycle records.
    Plugins are instantiated lazily — only when first needed.
    """

    def __init__(self) -> None:
        self._records: Dict[str, PluginLifecycle] = {}
        self._factories: Dict[str, Callable[[], Any]] = {}
        log.debug("[PluginManager] Initialised")

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        name:    str,
        version: str,
        factory: Callable[[], Any],
    ) -> None:
        """
        Register a plugin by name with a factory callable.

        No instantiation occurs at registration time.
        The factory is called only when the plugin is first needed.

        Parameters
        ----------
        name:
            Unique plugin identifier.
        version:
            Semantic version string.
        factory:
            Zero-argument callable that returns a PluginBase instance.
        """
        if name in self._records:
            log.warning("[PluginManager] Plugin '%s' already registered.", name)
            return

        record = PluginLifecycle(name=name, version=version)
        self._records[name]   = record
        self._factories[name] = factory

        log.info(
            "[PluginManager] Registered '%s' v%s (state=REGISTERED)",
            name,
            version,
        )

    # ------------------------------------------------------------------
    # Lazy loading
    # ------------------------------------------------------------------

    def get(self, name: str) -> Optional[Any]:
        """
        Return the plugin instance, instantiating it if necessary.

        Parameters
        ----------
        name:
            Unique plugin identifier.

        Returns
        -------
        PluginBase instance or None if not registered or load failed.
        """
        record = self._records.get(name)
        if record is None:
            log.warning("[PluginManager] Plugin '%s' not registered.", name)
            return None

        # Already loaded and available
        if record.is_available and record.is_loaded:
            return record.plugin_instance

        # Already failed — do not retry automatically
        if record.state == PluginState.FAILED:
            log.warning(
                "[PluginManager] Plugin '%s' is in FAILED state. Error: %s",
                name,
                record.error,
            )
            return None

        # Instantiate now
        return self._load(name, record)

    def _load(self, name: str, record: PluginLifecycle) -> Optional[Any]:
        """
        Instantiate and health-check a plugin.

        Returns the instance on success, None on failure.
        """
        factory = self._factories.get(name)
        if factory is None:
            record.mark_failed("No factory registered.")
            return None

        record.transition(PluginState.LOADING)
        log.info("[PluginManager] Loading '%s'...", name)

        try:
            instance = factory()
        except Exception as exc:
            error = f"Instantiation failed: {exc}"
            log.error("[PluginManager] '%s' load error: %s", name, error)
            record.mark_failed(error)
            return None

        # Health check
        try:
            healthy = instance.health_check()
        except Exception as exc:
            healthy = False
            log.warning(
                "[PluginManager] '%s' health_check raised: %s", name, exc
            )

        if not healthy:
            error = "health_check() returned False"
            log.warning("[PluginManager] '%s' failed health check.", name)
            record.mark_failed(error)
            return None

        record.mark_loaded(instance)
        log.info(
            "[PluginManager] '%s' ready | state=%s",
            name,
            record.state.name,
        )
        return instance

    # ------------------------------------------------------------------
    # Lifecycle control
    # ------------------------------------------------------------------

    def unload(self, name: str) -> None:
        """
        Unload a plugin and release its instance.

        Calls plugin.shutdown() if the method exists.

        Parameters
        ----------
        name:
            Unique plugin identifier.
        """
        record = self._records.get(name)
        if record is None:
            log.warning("[PluginManager] Cannot unload unknown plugin '%s'.", name)
            return

        if record.plugin_instance is not None:
            try:
                if hasattr(record.plugin_instance, "shutdown"):
                    record.plugin_instance.shutdown()
                    log.debug("[PluginManager] '%s' shutdown() called.", name)
            except Exception as exc:
                log.warning(
                    "[PluginManager] '%s' shutdown() raised: %s", name, exc
                )

        record.mark_unloaded()
        log.info("[PluginManager] '%s' unloaded.", name)

    def mark_busy(self, name: str) -> None:
        """Mark a plugin as currently executing."""
        record = self._records.get(name)
        if record:
            record.mark_execution_start()

    def mark_idle(self, name: str) -> None:
        """Mark a plugin as finished executing."""
        record = self._records.get(name)
        if record:
            record.mark_execution_end()

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    def state(self, name: str) -> Optional[PluginState]:
        """Return the current lifecycle state of a plugin."""
        record = self._records.get(name)
        return record.state if record else None

    def is_available(self, name: str) -> bool:
        """Return True if the plugin is ready to execute."""
        record = self._records.get(name)
        return record.is_available if record else False

    def list_all(self) -> List[Dict]:
        """Return lifecycle records for all registered plugins."""
        return [r.to_dict() for r in self._records.values()]

    def names(self) -> List[str]:
        """Return all registered plugin names."""
        return list(self._records.keys())