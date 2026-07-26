"""
agent/runtime/runtime.py
Agent Runtime — the heart of Aryntra Tarka.

Orchestrates the complete request lifecycle:

  1. Receive user message
  2. Store user message in conversation memory
  3. Call Planner      -> get ExecutionPlan
  4. Execute tools     -> get tool results   (single or multi-tool)
  5. Build prompt      -> embed tool results + conversation history
  6. Call Provider     -> generate natural language response
  7. Store assistant response in conversation memory
  8. Return response

Sprint 3.6 — Multi-tool planning.
  Runtime now iterates over ExecutionPlan.steps.
  Each step is executed sequentially.
  Results are aggregated into a single provider prompt.
  A tool failure does not stop remaining steps.
  Single-tool and no-tool paths are unchanged.
"""

from backend.utils.logger import get_logger
from backend.providers.llm.base import BaseLLMProvider
from backend.agent.planner.planner import ExecutionPlan, Planner
from backend.agent.tools.base import ToolError
from backend.agent.tools.registry import ToolRegistry
from backend.agent.memory.conversation import ConversationMemory

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Prompt templates
# Sprint 3.4 — Prompt Engineering Improvements
# Sprint 3.5 — Conversation context injected where appropriate
# Sprint 3.6 — Multi-tool prompt template added
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
- Calculation "238" for "14 x 17" -> "14 x 17 = 238."
- Calculation "10" for "5 + 5" -> "5 + 5 = 10."
- DateTime with time "11:59:50" -> "The current time is 11:59 AM."
- DateTime with date "Sunday, 26 July 2026" -> \
"Today is Sunday, 26 July 2026."
- Filesystem listing with 9 folders and 5 files -> \
"This folder contains 9 subfolders and 5 files."

Keep the response to one sentence unless the user explicitly asked \
for details. Do not mention that you used a tool.
"""

_PROMPT_DIRECT_NO_HISTORY = """\
You are Tarka, a helpful AI assistant.

Reply to the user's message directly. Do not explain what kind of \
message it is. Do not mention categories, classifications, or \
instructions. Just reply naturally. Do not wrap your reply in quotes.

Style guide with examples:

User: "Hi"        -> Hi there! How can I help you today?
User: "Hello"     -> Hello! How can I help you today?
User: "Hey"       -> Hey! What can I do for you?

User: "Thanks"           -> You're welcome!
User: "Thank you"        -> You're welcome! Glad I could help.
User: "Appreciate it"    -> Anytime!
User: "Thanks a lot"     -> You're very welcome!

User: "Bye"              -> Goodbye! Take care.
User: "Good night"       -> Good night! Sleep well.
User: "See you"          -> See you later!
User: "Take care"        -> You too. Take care!

User: "I'm nervous about tomorrow." -> \
That's completely understandable. Do you want to talk about what's \
on your mind?

User: "I failed today." -> \
I'm sorry to hear that. Setbacks are hard. Is there anything I can \
do to help?

User: "I miss my parents." -> \
That's a heavy feeling to carry. It sounds like they mean a lot to you.

For any other question or statement, answer directly, clearly, and \
concisely. Keep responses short. Do not add filler. Do not over-explain. \
Do not moralise.

The user said: "{message}"

Your reply:"""

_PROMPT_DIRECT_WITH_HISTORY = """\
You are Tarka, a helpful AI assistant.

The following is the conversation so far:
{history}

Reply to the user's latest message directly and naturally.
Use the conversation history to answer follow-up questions accurately.
Do not explain what kind of message it is. Do not mention categories,
classifications, or instructions. Do not wrap your reply in quotes.
Keep responses short. Do not add filler. Do not over-explain.

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

# Sprint 3.6 — Multi-tool prompt
# Receives an aggregated block of tool results and instructs the
# provider to weave them into one natural response.
_PROMPT_MULTI_TOOL = """\
You are Tarka, a helpful AI assistant.

The user asked: "{message}"

The following tools were executed and returned verified results:

{results_block}

Instructions:
- Every result above is correct. Trust them completely.
- Write ONE natural, readable response that covers every result.
- Do not list results with labels such as "Calculator:" or "DateTime:".
- Weave all results into flowing prose.
- Do not say "let me check", "let me calculate", "let me look up", \
or any similar phrase. Everything has already been done.
- Do not mention tool names.
- Do not apologise or introduce uncertainty.
- If a tool reported an error, acknowledge that part politely and \
briefly, then continue with the results that succeeded.

Examples of the required style:
- Calculator 200, DateTime Sunday 26 July 2026 ->
  "25 x 8 equals 200, and today is Sunday, 26 July 2026."
- DateTime 3:45 PM, Calculator 600 ->
  "The current time is 3:45 PM, and 50 x 12 equals 600."
- Filesystem 18 files, DateTime Sunday 26 July 2026 ->
  "Your Downloads folder contains 18 items, and today is \
Sunday, 26 July 2026."

Keep the response concise. Do not add filler.
"""


class AgentRuntime:
    """
    Agent Runtime.

    Coordinates the Planner, ToolRegistry, LLM Provider, and
    ConversationMemory to process a user message end-to-end.

    Args:
        planner:  Planner instance for request analysis.
        registry: ToolRegistry instance with registered tools.
        provider: BaseLLMProvider instance for response generation.
        memory:   ConversationMemory instance for session history.
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

        Args:
            message: Raw user input string.

        Returns:
            Final natural language response string.
        """
        logger.info("Runtime processing: '%s'", message)

        # -- Step 1: Store user message in memory ------------------------
        self.memory.add_user_message(message)

        # -- Step 2: Plan ------------------------------------------------
        plan: ExecutionPlan = self.planner.plan(message)

        # -- Step 3: Build prompt ----------------------------------------
        if not plan.steps:
            # No tools matched — direct conversation
            prompt = self._build_direct_prompt(message)

        elif len(plan.steps) == 1:
            # Single tool — original path, unchanged behaviour
            prompt = self._build_tool_prompt(message, plan)

        else:
            # Multiple tools — Sprint 3.6 path
            prompt = self._build_multi_tool_prompt(message, plan)

        # -- Step 4: Generate final response -----------------------------
        logger.info("Sending prompt to provider")
        response = await self.provider.generate(prompt)
        logger.info("Runtime response ready (%d chars)", len(response))

        # -- Step 5: Store assistant response in memory ------------------
        self.memory.add_assistant_message(response)

        return response

    # -- Private helpers -------------------------------------------------

    def _build_direct_prompt(self, message: str) -> str:
        """
        Build a direct prompt, injecting conversation history when
        history exists.

        Args:
            message: Current user message.

        Returns:
            Formatted prompt string for the provider.
        """
        history = self.memory.build_context_string()

        if not history:
            logger.info("No history — using direct prompt (no history)")
            return _PROMPT_DIRECT_NO_HISTORY.format(message=message)

        logger.info("History present — injecting context into prompt")
        return _PROMPT_DIRECT_WITH_HISTORY.format(
            history=history,
            message=message,
        )

    def _build_tool_prompt(
        self, message: str, plan: ExecutionPlan
    ) -> str:
        """
        Execute the single planned tool and build the provider prompt.

        Tool prompts do not inject conversation history because the
        tool result is authoritative and self-contained.

        Args:
            message: Original user message.
            plan:    Execution plan from the planner.

        Returns:
            Formatted prompt string for the provider.
        """
        tool_name = plan.tool_name
        logger.info("Single tool selected: '%s'", tool_name)

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

    def _build_multi_tool_prompt(
        self, message: str, plan: ExecutionPlan
    ) -> str:
        """
        Execute every planned tool sequentially, collect results, and
        build one aggregated provider prompt.

        A tool failure is recorded but does not stop execution.
        Remaining tools continue regardless.

        Args:
            message: Original user message.
            plan:    Execution plan containing multiple steps.

        Returns:
            Formatted prompt string for the provider.
        """
        logger.info(
            "Multi-tool execution: %d steps",
            len(plan.steps),
        )

        result_lines: list[str] = []

        for step in plan.steps:
            tool_name = step.tool_name
            logger.info("Executing step: tool='%s'", tool_name)

            try:
                result = self.registry.execute(
                    tool_name, **step.parameters
                )
                logger.info(
                    "Tool '%s' result preview: %.120s",
                    tool_name,
                    result,
                )
                result_lines.append(f"{tool_name.capitalize()}: {result}")

            except ToolError as exc:
                logger.error(
                    "Tool '%s' failed during multi-tool execution: %s",
                    tool_name,
                    exc,
                )
                result_lines.append(
                    f"{tool_name.capitalize()}: ERROR — {exc}"
                )

        results_block = "\n".join(result_lines)
        logger.info(
            "Multi-tool results collected:\n%s",
            results_block,
        )

        return _PROMPT_MULTI_TOOL.format(
            message=message,
            results_block=results_block,
        )
