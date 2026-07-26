"""
agent/services/agent.py
Application-level service factory.

Builds and returns the singleton AgentRuntime.
All wiring of concrete implementations happens here.
API routes and the runtime stay completely decoupled.

Swapping providers or adding tools means changing this file only.

Sprint 3.5: ConversationMemory wired into AgentRuntime.
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
from backend.agent.memory.conversation import ConversationMemory

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_agent_runtime() -> AgentRuntime:
    """
    Build and return the singleton AgentRuntime.

    lru_cache ensures this is constructed only once per
    application lifetime regardless of how many requests arrive.

    The ConversationMemory instance is created here and lives for
    the entire server session. Memory resets only when the server
    restarts.

    Returns:
        Fully wired AgentRuntime instance.
    """
    logger.info("Building AgentRuntime...")

    # -- Provider --------------------------------------------------------
    provider = OllamaLLMProvider(model=settings.ollama_default_model)

    # -- Tools -----------------------------------------------------------
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(DateTimeTool())
    registry.register(FileSystemTool())

    # -- Planner ---------------------------------------------------------
    planner = Planner()

    # -- Memory ----------------------------------------------------------
    # max_messages=20 retains the last 10 exchanges (user + assistant).
    # Older messages are discarded automatically.
    memory = ConversationMemory(max_messages=20)

    # -- Runtime ---------------------------------------------------------
    runtime = AgentRuntime(
        planner=planner,
        registry=registry,
        provider=provider,
        memory=memory,
    )

    logger.info(
        "AgentRuntime ready | tools=%s | model=%s | memory_limit=%d",
        registry.list_tools(),
        settings.ollama_default_model,
        20,
    )
    return runtime
