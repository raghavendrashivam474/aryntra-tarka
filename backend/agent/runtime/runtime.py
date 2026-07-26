"""
agent/runtime/runtime.py
Agent Runtime - the heart of Aryntra Tarka.

Orchestrates the complete request lifecycle:

  1. Receive user message
  2. Store user message in conversation memory
  3. Call Planner      -> get ExecutionPlan
  4. Execute tools     -> get tool results   (single or multi-tool)
  5. Build prompt      -> embed tool results + conversation history
  6. Call Provider     -> generate natural language response
  7. Store assistant response in conversation memory
  8. Return response

Sprint 3.6 - Multi-tool planning.
Sprint 3.8 - process_stream() added for real-time streaming.
"""

from typing import AsyncIterator

from backend.utils.logger import get_logger
from backend.providers.llm.base import BaseLLMProvider
from backend.agent.planner.planner import ExecutionPlan, Planner
from backend.agent.tools.base import ToolError
from backend.agent.tools.registry import ToolRegistry
from backend.agent.memory.conversation import ConversationMemory

logger = get_logger(__name__)

_PROMPT_WITH_TOOL = """\
You are Tarka, a helpful AI assistant.

The user asked: "{message}"

A tool has already been executed and returned this verified result:
{tool_result}

Instructions:
- The result above is correct. Trust it completely.
- Rephrase the result into ONE natural, conversational sentence.
- Do not repeat the raw output line-by-line.
- Do not reproduce formatting such as Date:, Time:, [DIR], or bullet lists.
- Present the answer directly and confidently.
- Do not say let me check, let me try, let me calculate, or any similar phrase.
- Do not suggest that any calculation or lookup is about to happen.
- Do not apologise or introduce uncertainty.

Examples:
- Calculation 238 for 14 x 17 -> 14 x 17 = 238.
- DateTime time 11:59:50 -> The current time is 11:59 AM.
- DateTime date Sunday 26 July 2026 -> Today is Sunday, 26 July 2026.
- Filesystem 9 folders 5 files -> This folder contains 9 subfolders and 5 files.

Keep the response to one sentence unless the user explicitly asked for details.
Do not mention that you used a tool.
"""

_PROMPT_DIRECT_NO_HISTORY = """\
You are Tarka, a helpful AI assistant.

Reply to the user message directly. Do not explain what kind of message it is.
Do not mention categories, classifications, or instructions.
Just reply naturally. Do not wrap your reply in quotes.

Style guide:
User: Hi        -> Hi there! How can I help you today?
User: Hello     -> Hello! How can I help you today?
User: Thanks    -> You are welcome!
User: Bye       -> Goodbye! Take care.

For any other question or statement, answer directly, clearly, and concisely.
Keep responses short. Do not add filler. Do not over-explain.

The user said: "{message}"

Your reply:"""

_PROMPT_DIRECT_WITH_HISTORY = """\
You are Tarka, a helpful AI assistant.

The following is the conversation so far:
{history}

Reply to the user latest message directly and naturally.
Use the conversation history to answer follow-up questions accurately.
Do not explain what kind of message it is.
Do not wrap your reply in quotes.
Keep responses short. Do not add filler. Do not over-explain.

The user said: "{message}"

Your reply:"""

_PROMPT_TOOL_ERROR = """\
You are Tarka, a helpful AI assistant.

The user asked: "{message}"

The {tool_name} tool was unable to complete the request.
The error was: {error}

Instructions:
- Inform the user politely that the request could not be completed.
- Briefly explain what went wrong in plain language if it is helpful.
- Suggest a practical alternative or next step where possible.
- Do not apologise excessively. One brief acknowledgement is enough.
- Keep the response concise.
"""

_PROMPT_MULTI_TOOL = """\
You are Tarka, a helpful AI assistant.

The user asked: "{message}"

The following tools were executed and returned verified results:

{results_block}

Instructions:
- Every result above is correct. Trust them completely.
- Write ONE natural, readable response that covers every result.
- Do not list results with labels such as Calculator: or DateTime:.
- Weave all results into flowing prose.
- Do not say let me check, let me calculate, or any similar phrase.
- Do not mention tool names.
- Do not apologise or introduce uncertainty.
- If a tool reported an error, acknowledge it briefly and continue.

Examples:
- Calculator 200, DateTime Sunday 26 July 2026 ->
  25 x 8 equals 200, and today is Sunday, 26 July 2026.
- DateTime 3:45 PM, Calculator 600 ->
  The current time is 3:45 PM, and 50 x 12 equals 600.

Keep the response concise. Do not add filler.
"""

class AgentRuntime:
    """
    Agent Runtime.

    Coordinates the Planner, ToolRegistry, LLM Provider, and
    ConversationMemory to process a user message end-to-end.

    Sprint 3.8 adds process_stream() which follows the identical
    pipeline as process() but yields chunks instead of returning
    a complete string.
    """

    def __init__(
        self,
        planner:  Planner,
        registry: ToolRegistry,
        provider: BaseLLMProvider,
        memory:   ConversationMemory,
    ) -> None:
        self.planner  = planner
        self.registry = registry
        self.provider = provider
        self.memory   = memory
        logger.info("AgentRuntime initialised")

    async def process(self, message: str) -> str:
        """
        Process a user message through the full agent pipeline.

        Returns:
            Final natural language response string.
        """
        logger.info("Runtime processing: '%s'", message)

        self.memory.add_user_message(message)

        plan: ExecutionPlan = self.planner.plan(message)

        if not plan.steps:
            prompt = self._build_direct_prompt(message)
        elif len(plan.steps) == 1:
            prompt = self._build_tool_prompt(message, plan)
        else:
            prompt = self._build_multi_tool_prompt(message, plan)

        logger.info("Sending prompt to provider")
        response = await self.provider.generate(prompt)
        logger.info("Runtime response ready (%d chars)", len(response))

        self.memory.add_assistant_message(response)
        return response

    async def process_stream(self, message: str) -> AsyncIterator[str]:
        """
        Process a user message and stream the response token by token.

        Identical pipeline to process() but yields chunks as they arrive.
        Full response is stored in memory once the stream completes.

        Yields:
            String chunks as they arrive from the provider.
        """
        logger.info("Runtime streaming: '%s'", message)

        self.memory.add_user_message(message)

        plan: ExecutionPlan = self.planner.plan(message)

        if not plan.steps:
            prompt = self._build_direct_prompt(message)
        elif len(plan.steps) == 1:
            prompt = self._build_tool_prompt(message, plan)
        else:
            prompt = self._build_multi_tool_prompt(message, plan)

        logger.info("Streaming prompt to provider")
        accumulated: list[str] = []

        async for chunk in self.provider.generate_stream(prompt):
            accumulated.append(chunk)
            yield chunk

        full_response = "".join(accumulated)
        logger.info("Runtime stream complete (%d chars)", len(full_response))
        self.memory.add_assistant_message(full_response)

    def _build_direct_prompt(self, message: str) -> str:
        history = self.memory.build_context_string()
        if not history:
            logger.info("No history - using direct prompt")
            return _PROMPT_DIRECT_NO_HISTORY.format(message=message)
        logger.info("History present - injecting context into prompt")
        return _PROMPT_DIRECT_WITH_HISTORY.format(
            history=history,
            message=message,
        )

    def _build_tool_prompt(self, message: str, plan: ExecutionPlan) -> str:
        tool_name = plan.tool_name
        logger.info("Single tool selected: '%s'", tool_name)
        try:
            tool_result = self.registry.execute(tool_name, **plan.parameters)
            logger.info(
                "Tool '%s' result preview: %.120s", tool_name, tool_result
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

    def _build_multi_tool_prompt(self, message: str, plan: ExecutionPlan) -> str:
        logger.info("Multi-tool execution: %d steps", len(plan.steps))
        result_lines: list[str] = []

        for step in plan.steps:
            tool_name = step.tool_name
            logger.info("Executing step: tool='%s'", tool_name)
            try:
                result = self.registry.execute(tool_name, **step.parameters)
                logger.info(
                    "Tool '%s' result preview: %.120s", tool_name, result
                )
                result_lines.append(f"{tool_name.capitalize()}: {result}")
            except ToolError as exc:
                logger.error(
                    "Tool '%s' failed during multi-tool execution: %s",
                    tool_name,
                    exc,
                )
                result_lines.append(f"{tool_name.capitalize()}: ERROR - {exc}")

        results_block = "\n".join(result_lines)
        logger.info("Multi-tool results collected:\n%s", results_block)
        return _PROMPT_MULTI_TOOL.format(
            message=message,
            results_block=results_block,
        )