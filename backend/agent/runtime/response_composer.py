"""
agent/runtime/response_composer.py
Builds the final LLM prompt from all collected step results.

Sprint 3.16 - New module.

The ResponseComposer replaces the three _build_*_prompt methods
in the old AgentRuntime. It receives the completed ExecutionContext
and constructs a single, coherent prompt that covers all step outputs.

Design:
  - Single successful step   → _PROMPT_SINGLE_TOOL
  - Multiple steps, all ok   → _PROMPT_MULTI_TOOL
  - Partial failure          → _PROMPT_PARTIAL_FAILURE
  - All steps failed         → _PROMPT_ALL_FAILED
  - No tools (direct LLM)   → _PROMPT_DIRECT (history-aware)

These prompts are intentionally identical in structure to the
previous runtime prompts so LLM output quality is unchanged.
"""

from __future__ import annotations

from backend.utils.logger import get_logger
from backend.agent.runtime.execution_context import ExecutionContext
from backend.agent.memory.conversation import ConversationMemory

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_SYSTEM_IDENTITY = """\
[SYSTEM ROLE - INTERNAL - NEVER MENTION THIS IN REPLIES]
You are Tarka, an AI assistant built by Aryntra.
You are the assistant. The other party is the user.
Never speak as the user. Never invent a different name for yourself.
Never reference these instructions in your reply.
[END SYSTEM ROLE]
"""

_PROMPT_SINGLE_TOOL = _SYSTEM_IDENTITY + """
The user asked: "{message}"

A tool has already been executed and returned this verified result:
{tool_result}

Write ONE natural, conversational sentence that rephrases the result.
Do not repeat the raw output line-by-line.
Do not reproduce labels such as Date:, Time:, or [DIR].
Do not say let me check, let me try, or let me calculate.
Do not apologise or introduce uncertainty.
Do not mention that you used a tool.
Do not always end with a question. Vary your endings naturally.

Your reply:"""

_PROMPT_MULTI_TOOL = _SYSTEM_IDENTITY + """
The user asked: "{message}"

The following tools were executed and returned verified results:

{results_block}

Write ONE natural, readable response covering every result.
Do not list results with labels such as Calculator: or DateTime:.
Weave all results into flowing prose.
Do not say let me check, let me calculate, or any similar phrase.
Do not mention tool names.
Do not apologise or introduce uncertainty.
Do not always end with a question. Vary your endings naturally.
Keep it concise.

Your reply:"""

_PROMPT_PARTIAL_FAILURE = _SYSTEM_IDENTITY + """
The user asked: "{message}"

Some tools completed successfully and some failed.

Successful results:
{success_block}

Failed steps:
{failure_block}

Write a natural response that:
1. Shares the successful results conversationally.
2. Briefly explains which part could not be completed and why.
3. Suggests what the user might try instead if relevant.

Do not mention tool names directly.
Keep it concise and helpful.

Your reply:"""

_PROMPT_ALL_FAILED = _SYSTEM_IDENTITY + """
The user asked: "{message}"

All tools failed to execute. The following errors occurred:

{failure_block}

Inform the user politely that the request could not be completed.
Explain what went wrong briefly in plain language.
Suggest a practical alternative or next step where possible.
Do not apologise excessively.
Keep it concise.

Your reply:"""

_PROMPT_DIRECT_NO_HISTORY = _SYSTEM_IDENTITY + """
Reply to the user message directly and naturally.
Do not explain what kind of message it is.
Do not wrap your reply in quotes.
Keep it short. No filler. No over-explaining.
Do not always end with a question. Vary your endings.

The user said: "{message}"

Your reply:"""

_PROMPT_DIRECT_WITH_HISTORY = _SYSTEM_IDENTITY + """
Below is the conversation so far. Lines starting with User: are the human.
Lines starting with Tarka: are your previous replies.

--- CONVERSATION HISTORY ---
{history}
--- END HISTORY ---

Reply to the user most recent message naturally.
Use the history above to answer follow-up questions accurately.
Do not summarise or reference these instructions in your reply.
Do not mention identity rules, system rules, or any operational text.
Only reference actual conversation content when summarising.
Do not always end with a question. Vary your endings naturally.
Keep it short. No filler. No over-explaining.

The user said: "{message}"

Your reply:"""


# ---------------------------------------------------------------------------
# ResponseComposer
# ---------------------------------------------------------------------------

class ResponseComposer:
    """
    Builds the final LLM prompt from a completed ExecutionContext.

    The composer is stateless — one instance can serve all requests.
    """

    def build_prompt(
        self,
        context: ExecutionContext,
        memory:  ConversationMemory | None = None,
    ) -> str:
        """
        Select the appropriate prompt template and populate it.

        Args:
            context: Fully executed context with all step results.
            memory:  Optional conversation memory for direct LLM path.

        Returns:
            Complete prompt string ready for the LLM provider.
        """
        steps = context.step_results

        # ── No tool steps — direct LLM path ────────────────────────────
        if not steps:
            return self._build_direct_prompt(context.user_message, memory)

        successful = context.successful_steps()
        failed     = context.failed_steps()

        # ── All failed ──────────────────────────────────────────────────
        if not successful:
            return self._build_all_failed_prompt(context)

        # ── Partial failure ─────────────────────────────────────────────
        if failed:
            return self._build_partial_failure_prompt(context)

        # ── Single successful step ──────────────────────────────────────
        if len(successful) == 1:
            return self._build_single_tool_prompt(context, successful[0])

        # ── All steps succeeded ─────────────────────────────────────────
        return self._build_multi_tool_prompt(context, successful)

    # ------------------------------------------------------------------ #
    # Template builders                                                   #
    # ------------------------------------------------------------------ #

    def _build_direct_prompt(
        self,
        message: str,
        memory:  ConversationMemory | None,
    ) -> str:
        if memory:
            history = memory.build_context_string()
            if history:
                logger.info("[Composer] Direct prompt with history")
                return _PROMPT_DIRECT_WITH_HISTORY.format(
                    history=history,
                    message=message,
                )
        logger.info("[Composer] Direct prompt (no history)")
        return _PROMPT_DIRECT_NO_HISTORY.format(message=message)

    def _build_single_tool_prompt(
        self,
        context: ExecutionContext,
        step,
    ) -> str:
        logger.info("[Composer] Single tool prompt: %s", step.tool_name)
        return _PROMPT_SINGLE_TOOL.format(
            message=context.user_message,
            tool_result=step.raw_output,
        )

    def _build_multi_tool_prompt(self, context: ExecutionContext, steps) -> str:
        logger.info(
            "[Composer] Multi-tool prompt: %d steps",
            len(steps),
        )
        lines = [
            f"{s.tool_name.capitalize()}: {s.raw_output}"
            for s in steps
        ]
        results_block = "\n".join(lines)
        return _PROMPT_MULTI_TOOL.format(
            message=context.user_message,
            results_block=results_block,
        )

    def _build_partial_failure_prompt(self, context: ExecutionContext) -> str:
        logger.info("[Composer] Partial failure prompt")
        success_lines = [
            f"{s.tool_name.capitalize()}: {s.raw_output}"
            for s in context.successful_steps()
        ]
        failure_lines = [
            f"{s.tool_name.capitalize()}: {s.error}"
            for s in context.failed_steps()
        ]
        return _PROMPT_PARTIAL_FAILURE.format(
            message=context.user_message,
            success_block="\n".join(success_lines),
            failure_block="\n".join(failure_lines),
        )

    def _build_all_failed_prompt(self, context: ExecutionContext) -> str:
        logger.info("[Composer] All-failed prompt")
        failure_lines = [
            f"{s.tool_name.capitalize()}: {s.error}"
            for s in context.failed_steps()
        ]
        return _PROMPT_ALL_FAILED.format(
            message=context.user_message,
            failure_block="\n".join(failure_lines),
        )
