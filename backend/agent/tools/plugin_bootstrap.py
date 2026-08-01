# coding: utf-8
"""
agent/tools/plugin_bootstrap.py

Layer 6 upgrade:
    Bootstrap now uses PluginManager-backed PluginLoader.
    Plugins are registered as factories — not instantiated at startup.
    Instances are created lazily on first use by PluginManager.

    Existing bootstrap API is completely unchanged.
    agent_registry.register() still works as before.
"""

from pathlib import Path

from backend.agent.tools.plugin_adapter import PluginAdapter
from backend.agent.tools.registry import ToolRegistry
from backend.runtime.plugins.loader import PluginLoader
from backend.runtime.plugins.manager import PluginManager
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def bootstrap_plugins(
    agent_registry: ToolRegistry,
    plugins_dir: str = "plugins",
) -> int:
    """
    Discover and register all plugins into the agent ToolRegistry.

    Layer 6: plugins are loaded lazily via PluginManager.
    Instances are created only when first executed.

    Skips any plugin whose name is already registered as a built-in tool.

    Returns:
        Number of plugins successfully registered.
    """
    manager = PluginManager()

    # Resolve plugins directory relative to project root
    plugins_path = Path("backend") / "plugins"
    if not plugins_path.exists():
        plugins_path = Path(plugins_dir)

    loader = PluginLoader(
        manager=manager,
        plugins_dir=str(plugins_path),
    )

    logger.info(
        "[Bootstrap] Scanning plugins directory: '%s'",
        plugins_path,
    )
    loader.load_all()

    registered = 0
    skipped    = 0

    for name in manager.names():
        # Skip if a built-in tool already covers this name
        if agent_registry.has_tool(name):
            logger.info(
                "[Bootstrap] Skipping plugin '%s' - built-in tool exists.",
                name,
            )
            skipped += 1
            continue

        # Lazily load the plugin instance now for health check
        plugin = manager.get(name)

        if plugin is None:
            logger.warning(
                "[Bootstrap] Skipping plugin '%s' - health check failed.",
                name,
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