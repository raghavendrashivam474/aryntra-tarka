# coding: utf-8
"""
agent/services/agent.py
Application-level service factory.

Sprint 3.21.1 - EventBus and ExecutionMonitor wired into AgentRuntime.
v1.5 Plugin SDK - bootstrap_plugins() + registry injected into Planner.
"""

from functools import lru_cache

from backend.utils.logger import get_logger
from backend.config.settings import settings
from backend.providers.llm.ollama import OllamaLLMProvider
from backend.agent.planner.planner import Planner
from backend.agent.runtime.runtime import AgentRuntime
from backend.agent.tools.calculator import CalculatorTool
from backend.agent.tools.datetime_tool import DateTimeTool
from backend.agent.tools.filesystem import FileSystemTool
from backend.agent.tools.registry import ToolRegistry
from backend.agent.tools.plugin_bootstrap import bootstrap_plugins
from backend.agent.memory.conversation import ConversationMemory

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_agent_runtime() -> AgentRuntime:
    """
    Build and return the singleton AgentRuntime.

    Build order:
      1. Provider
      2. ToolRegistry  <- built-in tools registered
      3. Plugin SDK    <- plugins discovered and registered
      4. Planner       <- receives live registry so it can route to plugins
      5. Memory
      6. EventBus + Monitor
      7. Runtime
    """
    logger.info("Building AgentRuntime...")

    # -- Provider --------------------------------------------------------
    provider = OllamaLLMProvider(model=settings.ollama_default_model)

    # -- Tools -----------------------------------------------------------
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(DateTimeTool())
    registry.register(FileSystemTool())

    # -- Plugin SDK ------------------------------------------------------
    plugin_count = bootstrap_plugins(registry, plugins_dir="backend/plugins")
    logger.info("Plugin SDK: %d plugin(s) loaded.", plugin_count)

    # -- Planner ---------------------------------------------------------
    # Registry passed so planner can route to any registered plugin.
    planner = Planner(plugin_registry=registry)

    # -- Memory ----------------------------------------------------------
    memory = ConversationMemory(max_messages=20)

    # -- EventBus --------------------------------------------------------
    from backend.api.routes.runtime_ws import get_event_bus
    from backend.agent.runtime.observability.execution_monitor import ExecutionMonitor

    event_bus = get_event_bus()
    monitor   = ExecutionMonitor(event_bus)

    # -- Runtime ---------------------------------------------------------
    runtime = AgentRuntime(
        planner=planner,
        registry=registry,
        provider=provider,
        memory=memory,
        monitor=monitor,
    )

    logger.info(
        "AgentRuntime ready | tools=%s | model=%s | memory_limit=%d",
        registry.list_tools(),
        settings.ollama_default_model,
        20,
    )
    return runtime