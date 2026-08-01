# coding: utf-8
"""
runtime/plugins/lifecycle.py

Layer 6 — Plugin Lifecycle Framework.

Defines the plugin lifecycle state machine and the PluginLifecycle
record that tracks every plugin instance managed by the runtime.

Lifecycle states:
    REGISTERED  — metadata known, instance not yet created
    LOADING     — instance being created
    READY       — instance created and health check passed
    BUSY        — currently executing a request
    IDLE        — previously executed, now waiting
    FAILED      — health check failed or load error
    UNLOADED    — explicitly unloaded, resources released

The runtime owns all state transitions.
Plugins own only their internal business logic.
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

class PluginState(Enum):
    """
    All possible lifecycle states for a plugin instance.

    Transitions:
        REGISTERED  -> LOADING   (on first use or explicit load)
        LOADING     -> READY     (load succeeded, health check passed)
        LOADING     -> FAILED    (load failed or health check failed)
        READY       -> BUSY      (execution started)
        BUSY        -> IDLE      (execution completed)
        IDLE        -> BUSY      (execution started again)
        IDLE        -> UNLOADED  (explicit unload)
        READY       -> UNLOADED  (explicit unload)
        FAILED      -> LOADING   (retry)
    """
    REGISTERED = auto()
    LOADING    = auto()
    READY      = auto()
    BUSY       = auto()
    IDLE       = auto()
    FAILED     = auto()
    UNLOADED   = auto()


# ---------------------------------------------------------------------------
# Lifecycle record
# ---------------------------------------------------------------------------

@dataclass
class PluginLifecycle:
    """
    Runtime lifecycle record for a single plugin.

    One instance per registered plugin.
    Created by PluginManager. Never created by plugins directly.

    Attributes
    ----------
    name:
        Unique plugin identifier.
    version:
        Semantic version string.
    state:
        Current lifecycle state.
    plugin_instance:
        The actual PluginBase instance. None until READY.
    registered_at:
        Monotonic timestamp when the plugin was first registered.
    loaded_at:
        Monotonic timestamp when the instance became READY. None if not loaded.
    last_executed_at:
        Monotonic timestamp of the most recent execution. None if never executed.
    execution_count:
        Total number of times this plugin has been executed.
    error:
        Last error message if state is FAILED. None otherwise.
    """

    name:             str
    version:          str
    state:            PluginState      = PluginState.REGISTERED
    plugin_instance:  Optional[object] = None
    registered_at:    float            = field(default_factory=time.monotonic)
    loaded_at:        Optional[float]  = None
    last_executed_at: Optional[float]  = None
    execution_count:  int              = 0
    error:            Optional[str]    = None

    def transition(self, new_state: PluginState) -> None:
        """
        Transition to a new lifecycle state.

        Logs every transition for observability.
        """
        old_state = self.state
        self.state = new_state

        log.debug(
            "[Lifecycle] '%s' %s -> %s",
            self.name,
            old_state.name,
            new_state.name,
        )

    def mark_loaded(self, instance: object) -> None:
        """Record a successful load."""
        self.plugin_instance = instance
        self.loaded_at       = time.monotonic()
        self.error           = None
        self.transition(PluginState.READY)

    def mark_failed(self, error: str) -> None:
        """Record a load or health check failure."""
        self.error           = error
        self.plugin_instance = None
        self.transition(PluginState.FAILED)

    def mark_execution_start(self) -> None:
        """Record that execution has begun."""
        self.transition(PluginState.BUSY)

    def mark_execution_end(self) -> None:
        """Record that execution has completed."""
        self.execution_count    += 1
        self.last_executed_at    = time.monotonic()
        self.transition(PluginState.IDLE)

    def mark_unloaded(self) -> None:
        """Record that the plugin has been unloaded."""
        self.plugin_instance = None
        self.transition(PluginState.UNLOADED)

    @property
    def is_available(self) -> bool:
        """True if the plugin can accept execution requests."""
        return self.state in (PluginState.READY, PluginState.IDLE)

    @property
    def is_loaded(self) -> bool:
        """True if a plugin instance exists."""
        return self.plugin_instance is not None

    def to_dict(self) -> dict:
        return {
            "name":             self.name,
            "version":          self.version,
            "state":            self.state.name,
            "is_available":     self.is_available,
            "execution_count":  self.execution_count,
            "error":            self.error,
            "loaded":           self.is_loaded,
        }