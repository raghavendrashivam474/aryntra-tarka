"""
agent/services/agent.py
Application-level service factory.

Builds and returns the singleton AgentRuntime.
All wiring of concrete implementations happens here.
API routes and the runtime stay completely decoupled.

Swapping providers or adding tools means changing this file only.
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

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_agent_runtime() -> AgentRuntime:
    """
    Build and return the singleton AgentRuntime.

    lru_cache ensures this is constructed only once per
    application lifetime regardless of how many requests arrive.

    Returns:
        Fully wired AgentRuntime instance.
    """
    logger.info("Building AgentRuntime...")

    # ── Provider ────────────────────────────────────────────────────────
    # Reuses the existing OllamaLLMProvider from Sprint 0.
    # Model and URL come from settings (ollama_default_model,
    # ollama_base_url) so no duplication of config.
    provider = OllamaLLMProvider(model=settings.ollama_default_model)

    # ── Tools ────────────────────────────────────────────────────────────
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(DateTimeTool())
    registry.register(FileSystemTool())

    # ── Planner ──────────────────────────────────────────────────────────
    planner = Planner()

    # ── Runtime ──────────────────────────────────────────────────────────
    runtime = AgentRuntime(
        planner=planner,
        registry=registry,
        provider=provider,
    )

    logger.info(
        "AgentRuntime ready | tools=%s | model=%s",
        registry.list_tools(),
        settings.ollama_default_model,
    )
    return runtime
