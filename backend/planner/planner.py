"""
Intelligent Planner - Sprint 3.15
Selects tools, prepares inputs, chains multiple tools.
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import json
import re

from tools.tool_registry import get_registry
from .expression_normalizer import ExpressionNormalizer


@dataclass
class PlanStep:
    tool: str                       # "llm" or tool name
    inputs: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Plan:
    steps: List[PlanStep]
    strategy: str = "single"        # single | multi | llm_only

    def to_dict(self) -> Dict[str, Any]:
        return {"strategy": self.strategy,
                "steps": [s.to_dict() for s in self.steps]}


class Planner:
    """
    Intelligent planner. Uses:
      1. Deterministic heuristics for obvious cases (math, weather, etc.).
      2. LLM-based planning with dynamic tool metadata for ambiguous cases.
    """

    def __init__(self, llm=None):
        self.registry = get_registry()
        self.llm = llm  # optional LLM provider

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------
    def plan(self, user_input: str) -> Plan:
        text = user_input.strip()

        # 1. Deterministic multi-tool detection
        multi = self._detect_multi_tool(text)
        if multi:
            return multi

        # 2. Deterministic single-tool heuristics
        single = self._detect_single_tool(text)
        if single:
            return single

        # 3. LLM planner fallback
        if self.llm is not None:
            llm_plan = self._llm_plan(text)
            if llm_plan:
                return llm_plan

        # 4. Default: answer with LLM
        return Plan(steps=[PlanStep(tool="llm", inputs={"prompt": text},
                                    reason="No tool required.")],
                    strategy="llm_only")

    # ---------------------------------------------------------
    # System prompt (dynamic)
    # ---------------------------------------------------------
    def build_system_prompt(self) -> str:
        tools = self.registry.to_prompt()
        return f"""You are Tarka's Planner. Produce an execution plan for the user's request.

You have access to the following tools:

{tools}

Routing Priorities (highest first):
  1. Mathematics       -> calculator
  2. Current Weather   -> weather
  3. Current Info/News -> search
  4. Date / Time       -> datetime
  5. Local Files       -> filesystem
  6. Clipboard         -> clipboard
  7. Passwords         -> password_generator
  8. System Info       -> system_info
  9. General Knowledge -> llm

Rules:
  - Prefer tools over LLM knowledge for factual/computational requests.
  - Chain multiple tools when a request requires more than one capability.
  - For math questions, always call `calculator` with a normalized expression.
    Never treat `%` as modulo when the user says "percent of".
  - For conceptual/explanatory questions, use `llm`.
  - Return only strict JSON of shape:
    {{
      "strategy": "single" | "multi" | "llm_only",
      "steps": [
        {{"tool": "<name>", "inputs": {{...}}, "reason": "..."}}
      ]
    }}
"""

    # ---------------------------------------------------------
    # Heuristics
    # ---------------------------------------------------------
    def _detect_single_tool(self, text: str) -> Optional[Plan]:
        low = text.lower()

        # Math
        if ExpressionNormalizer.looks_like_math(text):
            expr = ExpressionNormalizer.normalize(text) or text
            return Plan(steps=[PlanStep(
                tool="calculator",
                inputs={"expression": expr},
                reason="Detected mathematical expression.")],
                strategy="single")

        # Weather
        m = re.search(r'\bweather\s+(?:in|for|at)\s+([A-Za-z ,]+)', low)
        if m:
            return Plan(steps=[PlanStep(
                tool="weather",
                inputs={"location": m.group(1).strip().rstrip('?.!')},
                reason="Weather request detected.")],
                strategy="single")

        # Date/time
        if re.search(r'\b(what(?:\'s| is) )?(the )?(current )?(time|date|day)\b', low):
            return Plan(steps=[PlanStep(
                tool="datetime", inputs={},
                reason="Date/time request.")], strategy="single")

        # Search / news
        if re.search(r'\b(latest|today\'s|current|news|breaking)\b', low):
            return Plan(steps=[PlanStep(
                tool="search",
                inputs={"query": text.rstrip('?.!')},
                reason="Current information request.")],
                strategy="single")

        # Password
        if re.search(r'\b(generate|create|make).*\bpassword\b', low):
            length_match = re.search(r'(\d{1,3})\s*(?:chars?|characters?|long)?', low)
            length = int(length_match.group(1)) if length_match else 16
            return Plan(steps=[PlanStep(
                tool="password_generator",
                inputs={"length": length},
                reason="Password generation request.")],
                strategy="single")

        # Clipboard
        if re.search(r'\bclipboard\b', low):
            action = "write" if re.search(r'\b(copy|write|set)\b', low) else "read"
            return Plan(steps=[PlanStep(
                tool="clipboard",
                inputs={"action": action},
                reason="Clipboard interaction.")],
                strategy="single")

        # System info
        if re.search(r'\b(cpu|ram|memory|os|system info|uptime|disk)\b', low):
            return Plan(steps=[PlanStep(
                tool="system_info", inputs={},
                reason="System information request.")],
                strategy="single")

        return None

    def _detect_multi_tool(self, text: str) -> Optional[Plan]:
        low = text.lower()

        # Weather + convert to Fahrenheit/Celsius
        m = re.search(r'weather\s+(?:in|for|at)\s+([A-Za-z ,]+?)(?:\s+and\s+convert.*?(fahrenheit|celsius))',
                      low)
        if m:
            location = m.group(1).strip()
            target = m.group(2)
            steps = [
                PlanStep(tool="weather", inputs={"location": location},
                         reason="Fetch current weather."),
                PlanStep(tool="calculator",
                         inputs={"expression": "<weather.temp_c> * 9/5 + 32"
                                 if target == "fahrenheit"
                                 else "(<weather.temp_f> - 32) * 5/9"},
                         reason=f"Convert to {target}."),
                PlanStep(tool="llm",
                         inputs={"prompt": "Summarize weather + conversion."},
                         reason="Generate final natural-language answer."),
            ]
            return Plan(steps=steps, strategy="multi")

        # Search + summarize
        if re.search(r'\b(search|find|look up).*\band\s+summari[sz]e\b', low) \
           or re.search(r'\b(latest|today\'s).*\band\s+summari[sz]e\b', low):
            return Plan(steps=[
                PlanStep(tool="search",
                         inputs={"query": text.rstrip('?.!')},
                         reason="Fetch current information."),
                PlanStep(tool="llm",
                         inputs={"prompt": "Summarize the search results."},
                         reason="Summarize with LLM."),
            ], strategy="multi")

        return None

    # ---------------------------------------------------------
    # LLM fallback planner
    # ---------------------------------------------------------
    def _llm_plan(self, text: str) -> Optional[Plan]:
        try:
            system = self.build_system_prompt()
            resp = self.llm.complete(system=system, prompt=text)
            data = self._extract_json(resp)
            if not data:
                return None
            steps = [PlanStep(**s) for s in data.get("steps", [])]
            if not steps:
                return None
            return Plan(steps=steps, strategy=data.get("strategy", "single"))
        except Exception:
            return None

    @staticmethod
    def _extract_json(text: str) -> Optional[Dict[str, Any]]:
        if not text:
            return None
        m = re.search(r'\{.*\}', text, re.S)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
