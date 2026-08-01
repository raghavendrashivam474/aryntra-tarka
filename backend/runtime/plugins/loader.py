# coding: utf-8
"""
runtime/plugins/loader.py

Discovers and loads plugins from the plugins directory.
"""

import importlib
import importlib.util
import inspect
import logging
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class PluginLoader:
    """
    Discovers and loads plugins from the plugins directory.
    """

    def __init__(self, registry, plugins_dir: str = "plugins"):
        self.registry    = registry
        self.plugins_dir = Path(plugins_dir)

    def load_all(self) -> None:
        if not self.plugins_dir.exists():
            logger.warning("Plugins directory not found: %s", self.plugins_dir)
            return

        for plugin_folder in self.plugins_dir.iterdir():
            if plugin_folder.is_dir():
                self._load_plugin(plugin_folder)

    def _load_plugin(self, folder: Path) -> None:
        tool_file = folder / "tool.py"

        if not tool_file.exists():
            logger.debug("No tool.py found in %s. Skipping.", folder.name)
            return

        try:
            module_name = f"plugins.{folder.name}.tool"
            spec        = importlib.util.spec_from_file_location(module_name, tool_file)
            module      = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            plugin_class = self._find_plugin_class(module)

            if plugin_class is None:
                logger.warning(
                    "No PluginBase subclass found in %s. Skipping.", folder.name
                )
                return

            plugin_instance = plugin_class()
            self.registry.register(plugin_instance)

        except Exception as exc:
            logger.error("Failed to load plugin from %s: %s", folder.name, exc)

    def _find_plugin_class(self, module) -> Optional[type]:
        """
        Find a PluginBase subclass in the module.

        Uses name-based duck typing instead of strict issubclass()
        to avoid false negatives caused by the same file being imported
        under two different module paths (e.g. runtime.plugins.base vs
        backend.runtime.plugins.base).

        A class qualifies if:
          1. It is a class defined in this module.
          2. It has all four required PluginBase members.
          3. Its name is not exactly 'PluginBase'.
        """
        required = {"name", "description", "version", "execute"}

        for _, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__name__ == "PluginBase":
                continue

            # Check it actually lives in this module (not just imported)
            if obj.__module__ != module.__name__:
                continue

            has_all = all(hasattr(obj, attr) for attr in required)
            if has_all:
                return obj

        return None