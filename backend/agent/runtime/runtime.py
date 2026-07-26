"""
agent/runtime/runtime.py
Agent Runtime — the heart of Aryntra Tarka.

Orchestrates the complete request lifecycle:

  1. Receive user message
  2. Store user message in conversation memory
  3. Call Planner      → get ExecutionPlan
  4. Execute tool      → get tool result     (if plan requires one)
  5. Build prompt      → embed tool result + conversation history
  6. Call Provider     → generate natural language response
  7. Store assistant response in conversation memory
  8. Return response

The runtime is async because OllamaLLMProvider.generate() is async.
The runtime knows about: Planner, ToolRegistry, BaseLLMProvider,
ConversationMemory.
Nothing else.
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
        if plan.tool_name is not None:
            prompt = self._build_tool_prompt(message, plan)
        else:
            prompt = self._build_direct_prompt(message)

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
        Execute the planned tool and build the provider prompt.

        Tool prompts do not inject conversation history because the
        tool result is authoritative and self-contained. The user
        asked for a computation or lookup; the result is the answer.

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
