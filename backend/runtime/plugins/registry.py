# coding: utf-8
import logging
from typing import Any, Dict, List, Optional
from backend.runtime.plugins.base import PluginBase

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Central registry for all plugins.
    """

    def __init__(self):
        self._plugins: Dict[str, PluginBase] = {}
        logger.info("ToolRegistry initialized.")

    def register(self, plugin: PluginBase) -> None:
        if plugin.name in self._plugins:
            logger.warning(f"Plugin already registered: {plugin.name}. Overwriting.")
        self._plugins[plugin.name] = plugin
        logger.info(f"Plugin registered: {plugin.name} v{plugin.version}")

    def unregister(self, name: str) -> None:
        if name in self._plugins:
            del self._plugins[name]
            logger.info(f"Plugin unregistered: {name}")
        else:
            logger.warning(f"Attempted to unregister unknown plugin: {name}")

    def find(self, name: str) -> Optional[PluginBase]:
        return self._plugins.get(name)

    def list(self) -> List[Dict]:
        return [
            {
                "name":    p.name,
                "description": p.description,
                "version": p.version,
                "healthy": p.health_check(),
            }
            for p in self._plugins.values()
        ]

    def execute(self, name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        plugin = self.find(name)
        if plugin is None:
            raise ValueError(f"Plugin not found: {name}")
        if not plugin.health_check():
            raise RuntimeError(f"Plugin health check failed: {name}")
        logger.info(f"Executing plugin: {name}")
        result = plugin.execute(input_data)
        logger.info(f"Plugin execution complete: {name}")
        return result