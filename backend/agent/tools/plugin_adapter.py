# coding: utf-8
"""
agent/tools/plugin_adapter.py

Bridges the Plugin SDK (runtime/plugins/PluginBase) into the
existing agent tool system (agent/tools/BaseTool).

No changes required in PlanExecutor, ToolRegistry, or AgentRuntime.
"""

from typing import Any

from backend.agent.tools.base import BaseTool, ToolError
from backend.runtime.plugins.base import PluginBase
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class PluginAdapter(BaseTool):
    """
    Wraps a PluginBase instance as a BaseTool.
    The agent runtime only knows BaseTool.
    The plugin system only knows PluginBase.
    This adapter is the bridge.
    """

    def __init__(self, plugin: PluginBase) -> None:
        self._plugin = plugin
        logger.debug(
            "PluginAdapter created for plugin '%s' v%s",
            plugin.name,
            plugin.version,
        )

    @property
    def name(self) -> str:
        return self._plugin.name

    @property
    def description(self) -> str:
        return self._plugin.description

    def execute(self, **kwargs: Any) -> str:
        if not self._plugin.health_check():
            raise ToolError(
                f"Plugin '{self._plugin.name}' failed health check."
            )
        try:
            result = self._plugin.execute(input_data=kwargs)
            return self._format_result(result)
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError(
                f"Plugin '{self._plugin.name}' raised an error: {exc}"
            ) from exc

    def execute_structured(self, **kwargs: Any) -> dict[str, Any]:
        if not self._plugin.health_check():
            raise ToolError(
                f"Plugin '{self._plugin.name}' failed health check."
            )
        try:
            result = self._plugin.execute(input_data=kwargs)
            if "formatted" not in result:
                result["formatted"] = self._format_result(result)
            logger.info(
                "PluginAdapter structured result | plugin='%s' keys=%s",
                self._plugin.name,
                list(result.keys()),
            )
            return result
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError(
                f"Plugin '{self._plugin.name}' raised an error: {exc}"
            ) from exc

    def _format_result(self, result: dict[str, Any]) -> str:
        if "error" in result:
            return f"Error: {result['error']}"
        if "formatted" in result:
            return str(result["formatted"])
        if "result" in result:
            return str(result["result"])
        return str(result)