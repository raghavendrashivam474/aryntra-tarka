# coding: utf-8
"""
agent/tools/plugin_bootstrap.py

Loads all plugins from the plugins/ directory and registers them
into the agent ToolRegistry via PluginAdapter.

Called once at application startup.

Usage:
    from backend.agent.tools.plugin_bootstrap import bootstrap_plugins
    bootstrap_plugins(registry)
"""

from backend.agent.tools.plugin_adapter import PluginAdapter
from backend.agent.tools.registry import ToolRegistry
from backend.runtime.plugins.loader import PluginLoader
from backend.runtime.plugins.registry import ToolRegistry as PluginRegistry
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def bootstrap_plugins(
    agent_registry: ToolRegistry,
    plugins_dir: str = "plugins",
) -> int:
    """
    Discover, load, and register all plugins into the agent ToolRegistry.

    Skips any plugin whose name is already registered.
    Built-in tools always take priority.

    Returns:
        Number of plugins successfully registered.
    """
    plugin_registry = PluginRegistry()
    loader = PluginLoader(
        registry=plugin_registry,
        plugins_dir=plugins_dir,
    )

    logger.info("[Bootstrap] Scanning plugins directory: '%s'", plugins_dir)
    loader.load_all()

    plugins    = plugin_registry.list()
    registered = 0
    skipped    = 0

    for meta in plugins:
        name   = meta["name"]
        plugin = plugin_registry.find(name)

        if plugin is None:
            logger.warning("[Bootstrap] Plugin '%s' listed but not found.", name)
            continue

        if agent_registry.has_tool(name):
            logger.info(
                "[Bootstrap] Skipping plugin '%s' - built-in tool exists.", name
            )
            skipped += 1
            continue

        if not meta.get("healthy", True):
            logger.warning(
                "[Bootstrap] Skipping plugin '%s' - health check failed.", name
            )
            skipped += 1
            continue

        adapter = PluginAdapter(plugin)
        agent_registry.register(adapter)
        registered += 1
        logger.info("[Bootstrap] Registered plugin: '%s'", name)

    logger.info(
        "[Bootstrap] Complete | registered=%d skipped=%d",
        registered,
        skipped,
    )
    return registered