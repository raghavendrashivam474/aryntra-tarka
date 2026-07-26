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
# Sprint 3.4 — Prompt Engineering Improvements
# ---------------------------------------------------------------------------

_PROMPT_WITH_TOOL = """\
You are Tarka, a helpful AI assistant.

The user asked: "{message}"

A tool has already been executed and returned this verified result:
{tool_result}

Instructions:
- The result above is correct. Trust it completely.
- Rephrase the result into ONE natural, conversational sentence. \
Do not repeat the raw output line-by-line. Do not reproduce formatting \
such as "Date:", "Time:", "[DIR]", or bullet lists.
- Present the answer directly and confidently.
- Do not say "let me check", "let me try", "let me calculate", \
"I'll double-check", "let me verify", or any similar phrase.
- Do not suggest that any calculation or lookup is about to happen. \
It has already happened.
- Do not apologise or introduce uncertainty.

Examples of the required style:
- Calculation "238" for "14 × 17" → "14 × 17 = 238."
- Calculation "10" for "5 + 5" → "5 + 5 = 10."
- DateTime with time "11:59:50" → "The current time is 11:59 AM."
- DateTime with date "Sunday, 26 July 2026" → \
"Today is Sunday, 26 July 2026."
- Filesystem listing with 9 folders and 5 files → \
"This folder contains 9 subfolders and 5 files."

Keep the response to one sentence unless the user explicitly asked \
for details. Do not mention that you used a tool.
"""

_PROMPT_DIRECT = """\
You are Tarka, a helpful AI assistant.

Reply to the user's message directly. Do not explain what kind of \
message it is. Do not mention categories, classifications, or \
instructions. Just reply naturally. Do not wrap your reply in quotes.

Style guide with examples:

User: "Hi"        → Hi there! How can I help you today?
User: "Hello"     → Hello! How can I help you today?
User: "Hey"       → Hey! What can I do for you?

User: "Thanks"           → You're welcome!
User: "Thank you"        → You're welcome! Glad I could help.
User: "Appreciate it"    → Anytime!
User: "Thanks a lot"     → You're very welcome!

User: "Bye"              → Goodbye! Take care.
User: "Good night"       → Good night! Sleep well.
User: "See you"          → See you later!
User: "Take care"        → You too. Take care!

User: "I'm nervous about tomorrow." → \
That's completely understandable. Do you want to talk about what's \
on your mind?

User: "I failed today." → \
I'm sorry to hear that. Setbacks are hard. Is there anything I can \
do to help?

User: "I miss my parents." → \
That's a heavy feeling to carry. It sounds like they mean a lot to you.

For any other question or statement, answer directly, clearly, and \
concisely. Keep responses short. Do not add filler. Do not over-explain. \
Do not moralise.

The user said: "{message}"

Your reply:"""

_PROMPT_TOOL_ERROR = """\
You are Tarka, a helpful AI assistant.

The user asked: "{message}"

The {tool_name} tool was unable to complete the request. \
The error was: {error}

Instructions:
- Inform the user politely that the request could not be completed.
- Briefly explain what went wrong in plain language if it is helpful.
- Suggest a practical alternative or next step where possible.
- Do not apologise excessively. One brief acknowledgement is enough.
- Keep the response concise.
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
