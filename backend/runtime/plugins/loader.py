# coding: utf-8
"""
runtime/plugins/loader.py

Layer 6 upgrade:
    PluginLoader now registers plugin classes with PluginManager
    instead of instantiating them directly.

    Instantiation is deferred to first use (lazy loading).
    The runtime owns all plugin instances via PluginManager.
"""

import importlib.util
import inspect
import logging
import sys
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)


class PluginLoader:
    """
    Discovers plugin classes from the plugins directory
    and registers them with PluginManager.

    No plugin instances are created during loading.
    """

    def __init__(self, manager, plugins_dir: str = "plugins"):
        self._manager    = manager
        self.plugins_dir = Path(plugins_dir)

    def load_all(self) -> None:
        """Scan the plugins directory and register all found plugins."""
        if not self.plugins_dir.exists():
            log.warning("Plugins directory not found: %s", self.plugins_dir)
            return

        for plugin_folder in sorted(self.plugins_dir.iterdir()):
            if plugin_folder.is_dir():
                self._load_plugin(plugin_folder)

    def _load_plugin(self, folder: Path) -> None:
        tool_file = folder / "tool.py"

        if not tool_file.exists():
            log.debug("No tool.py in %s. Skipping.", folder.name)
            return

        try:
            module_name = f"backend.plugins.{folder.name}.tool"
            spec        = importlib.util.spec_from_file_location(
                module_name, tool_file
            )
            module      = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            plugin_class = self._find_plugin_class(module)

            if plugin_class is None:
                log.warning(
                    "No PluginBase subclass found in %s. Skipping.",
                    folder.name,
                )
                return

            # Create a temporary instance only to read name/version
            # then immediately discard it.
            # The real instance is created by PluginManager on first use.
            try:
                temp = plugin_class()
                name    = temp.name
                version = temp.version
                del temp
            except Exception as exc:
                log.error(
                    "Could not read metadata from %s: %s",
                    folder.name,
                    exc,
                )
                return

            # Register factory with PluginManager — no instantiation yet
            self._manager.register(
                name=name,
                version=version,
                factory=plugin_class,
            )

            log.debug(
                "Registered factory for '%s' v%s",
                name,
                version,
            )

        except Exception as exc:
            log.error("Failed to load plugin from %s: %s", folder.name, exc)

    def _find_plugin_class(self, module) -> Optional[type]:
        """
        Find a PluginBase subclass in the module.

        Duck-typed — does not require strict issubclass() to avoid
        module path mismatches.
        """
        required = {"name", "description", "version", "execute"}

        for _, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__name__ == "PluginBase":
                continue
            if obj.__module__ != module.__name__:
                continue
            if all(hasattr(obj, attr) for attr in required):
                return obj

        return None