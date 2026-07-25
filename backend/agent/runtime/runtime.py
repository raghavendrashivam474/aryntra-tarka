"""
agent/runtime/runtime.py
Agent Runtime — the heart of Aryntra Tarka.

Orchestrates the complete request lifecycle:

  1. Receive user message
  2. Call Planner      → get ExecutionPlan
  3. Execute tool      → get tool result     (if plan requires one)
  4. Build prompt      → embed tool result into prompt
  5. Call Provider     → generate natural language response
  6. Return response

The runtime is async because OllamaLLMProvider.generate() is async.
The runtime knows about: Planner, ToolRegistry, BaseLLMProvider.
Nothing else.
"""

from backend.utils.logger import get_logger
from backend.providers.llm.base import BaseLLMProvider
from backend.agent.planner.planner import ExecutionPlan, Planner
from backend.agent.tools.base import ToolError
from backend.agent.tools.registry import ToolRegistry

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_PROMPT_WITH_TOOL = """\
You are Tarka, a helpful AI assistant.

The user asked: "{message}"

You used the {tool_name} tool and received this result:
{tool_result}

Using only this information, provide a clear, concise, and friendly \
response to the user. Do not mention that you used a tool unless helpful.
"""

_PROMPT_DIRECT = """\
You are Tarka, a helpful AI assistant.

The user asked: "{message}"

Please provide a clear, concise, and helpful response.
"""

_PROMPT_TOOL_ERROR = """\
You are Tarka, a helpful AI assistant.

The user asked: "{message}"

You attempted to use the {tool_name} tool but encountered this error:
{error}

Inform the user politely and suggest what they might try instead.
"""


class AgentRuntime:
    """
    Agent Runtime.

    Coordinates the Planner, ToolRegistry, and LLM Provider
    to process a user message end-to-end.

    Args:
        planner:  Planner instance for request analysis.
        registry: ToolRegistry instance with registered tools.
        provider: BaseLLMProvider instance for response generation.
    """

    def __init__(
        self,
        planner:  Planner,
        registry: ToolRegistry,
        provider: BaseLLMProvider,
    ) -> None:
        self.planner  = planner
        self.registry = registry
        self.provider = provider
        logger.info("AgentRuntime initialised")

    async def process(self, message: str) -> str:
        """
        Process a user message through the full agent pipeline.

        Args:
            message: Raw user input string.

        Returns:
            Final natural language response string.
        """
        logger.info("Runtime processing: '%s'", message)

        # ── Step 1: Plan ────────────────────────────────────────────────
        plan: ExecutionPlan = self.planner.plan(message)

        # ── Step 2: Execute tool (if plan requires one) ─────────────────
        if plan.tool_name is not None:
            prompt = self._build_tool_prompt(message, plan)
        else:
            logger.info("No tool required — direct provider response")
            prompt = _PROMPT_DIRECT.format(message=message)

        # ── Step 3: Generate final response ─────────────────────────────
        logger.info("Sending prompt to provider")
        response = await self.provider.generate(prompt)
        logger.info("Runtime response ready (%d chars)", len(response))
        return response

    # ── Private helpers ─────────────────────────────────────────────────

    def _build_tool_prompt(
        self, message: str, plan: ExecutionPlan
    ) -> str:
        """
        Execute the planned tool and build the provider prompt.

        Args:
            message: Original user message.
            plan:    Execution plan from the planner.

        Returns:
            Formatted prompt string for the provider.
        """
        tool_name = plan.tool_name
        logger.info("Tool selected: '%s'", tool_name)

        try:
            tool_result = self.registry.execute(
                tool_name, **plan.parameters
            )
            logger.info(
                "Tool '%s' result preview: %.120s",
                tool_name,
                tool_result,
            )
            return _PROMPT_WITH_TOOL.format(
                message=message,
                tool_name=tool_name,
                tool_result=tool_result,
            )

        except ToolError as exc:
            logger.error("Tool '%s' failed: %s", tool_name, exc)
            return _PROMPT_TOOL_ERROR.format(
                message=message,
                tool_name=tool_name,
                error=str(exc),
            )
