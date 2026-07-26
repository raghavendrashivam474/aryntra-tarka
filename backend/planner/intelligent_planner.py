"""
intelligent_planner.py
======================
Replaces the naive planner with a full orchestration-aware planning layer.

Responsibilities
----------------
  1. Build a dynamic system prompt from the tool registry.
  2. Call the LLM with temperature=0 for deterministic output.
  3. Extract and parse the JSON execution plan from the response.
  4. Validate all tool names against the registry.
  5. Normalize calculator expressions via the expression normalizer.
  6. Return a typed ExecutionPlan ready for the runtime.

Constraints
-----------
  - Does NOT modify the runtime, streaming engine, or any tool implementation.
  - Falls back gracefully on any parsing or LLM failure.
  - Retries once before falling back.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from backend.planner.execution_plan import ExecutionPlan, PlanStep
from backend.planner.normalizers.expression_normalizer import normalize_expression
from backend.planner.prompt_builder import build_planner_system_prompt
from backend.planner.tool_metadata import get_all_tool_metadata

logger = logging.getLogger(__name__)

_MAX_RETRIES         = 2
_HISTORY_WINDOW      = 6            # number of prior messages to include
_JSON_BLOCK_PATTERN  = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


# =============================================================================
# IntelligentPlanner
# =============================================================================

class IntelligentPlanner:
    """
    Orchestration-aware planner that routes every request through
    the appropriate tool chain.

    Usage
    -----
        planner = IntelligentPlanner(llm_provider)
        plan    = await planner.plan("What is 15% of 340?")
        # -> ExecutionPlan(plan=[PlanStep(tool="calculator", ...)], fallback=False)
    """

    def __init__(self, llm_provider: Any) -> None:
        self._llm           = llm_provider
        self._tool_registry = get_all_tool_metadata()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def plan(
        self,
        user_message:         str,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> ExecutionPlan:
        """
        Analyse the user message and return a typed ExecutionPlan.

        Args:
            user_message         : Raw user input.
            conversation_history : Optional list of {"role": ..., "content": ...}
                                   dicts for conversational context.

        Returns:
            ExecutionPlan — either a tool chain or a fallback plan.
        """
        logger.info("[Planner] Planning request: %.80s", user_message)

        messages = self._build_messages(user_message, conversation_history)

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                raw        = await self._call_llm(messages)
                plan       = self._parse_plan(raw)
                plan       = self._post_process(plan)

                logger.info(
                    "[Planner] Plan ready — tools=%s fallback=%s attempt=%d",
                    plan.tool_names, plan.fallback, attempt,
                )
                return plan

            except Exception as exc:
                logger.warning("[Planner] Attempt %d failed: %s", attempt, exc)

        logger.error("[Planner] All %d attempts failed — returning fallback.", _MAX_RETRIES)
        return ExecutionPlan.fallback_plan("Planner could not produce a valid plan.")

    # ------------------------------------------------------------------
    # Message construction
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        user_message: str,
        history:      list[dict[str, str]] | None,
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = [
            {"role": "system", "content": build_planner_system_prompt()},
        ]

        if history:
            for entry in history[-_HISTORY_WINDOW:]:
                role    = entry.get("role", "user")
                content = entry.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": user_message})
        return messages

    # ------------------------------------------------------------------
    # LLM call
    # ------------------------------------------------------------------

    async def _call_llm(self, messages: list[dict[str, str]]) -> str:
        response = await self._llm.chat(
            messages    = messages,
            temperature = 0.0,   # deterministic
            max_tokens  = 1024,
        )

        if isinstance(response, str):
            return response
        if hasattr(response, "content"):
            return response.content
        if isinstance(response, dict):
            return response.get("content", str(response))
        return str(response)

    # ------------------------------------------------------------------
    # Plan parsing & validation
    # ------------------------------------------------------------------

    def _parse_plan(self, raw: str) -> ExecutionPlan:
        json_str = self._extract_json(raw)

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid JSON from planner. Error: {exc}\n"
                f"Raw (first 300 chars): {raw[:300]}"
            ) from exc

        return self._build_plan(data)

    def _extract_json(self, raw: str) -> str:
        """Pull JSON from a markdown code block or bare object."""
        match = _JSON_BLOCK_PATTERN.search(raw)
        if match:
            return match.group(1).strip()

        # Fallback: find outermost { ... }
        start = raw.find("{")
        end   = raw.rfind("}")
        if start != -1 and end > start:
            return raw[start : end + 1]

        raise ValueError(f"No JSON found in planner response: {raw[:200]}")

    def _build_plan(self, data: dict[str, Any]) -> ExecutionPlan:
        if not isinstance(data, dict):
            raise ValueError("Planner response must be a JSON object.")

        fallback  = data.get("fallback", False)
        reasoning = data.get("reasoning", "")
        raw_steps = data.get("plan", [])

        if fallback or not raw_steps:
            return ExecutionPlan.fallback_plan(reasoning or "No tool required.")

        steps: list[PlanStep] = []
        for i, raw in enumerate(raw_steps):
            tool_name = raw.get("tool", "").strip().lower()

            if not tool_name:
                raise ValueError(f"Step {i+1} has no tool name.")

            if tool_name not in self._tool_registry:
                logger.warning("[Planner] Unknown tool '%s' in step %d — skipping.", tool_name, i+1)
                continue

            steps.append(PlanStep(
                step       = raw.get("step", i + 1),
                tool       = tool_name,
                parameters = raw.get("parameters", {}),
                reason     = raw.get("reason", ""),
            ))

        if not steps:
            return ExecutionPlan.fallback_plan("No valid tool steps could be extracted.")

        return ExecutionPlan(plan=steps, fallback=False, reasoning=reasoning)

    # ------------------------------------------------------------------
    # Post-processing
    # ------------------------------------------------------------------

    def _post_process(self, plan: ExecutionPlan) -> ExecutionPlan:
        """Apply normalizations after the plan is parsed."""
        for step in plan.plan:
            if step.tool == "calculator":
                step.parameters = self._normalize_calculator_params(step.parameters)
        return plan

    def _normalize_calculator_params(self, params: dict[str, Any]) -> dict[str, Any]:
        raw = params.get("expression", "")
        if not raw:
            return params

        try:
            normalized = normalize_expression(str(raw))
            if normalized != raw:
                logger.info(
                    "[Planner] Expression normalized: %r -> %r", raw, normalized
                )
            params["expression"] = normalized
        except Exception as exc:
            logger.warning("[Planner] Expression normalization failed: %s", exc)

        return params
