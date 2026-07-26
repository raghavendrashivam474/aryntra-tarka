"""
prompt_builder.py
=================
Dynamically generates the planner system prompt from the tool registry.

Nothing here is hardcoded.
Every tool section is derived from TOOL_METADATA at call time.
"""

from __future__ import annotations
from backend.planner.tool_metadata import get_tools_sorted_by_priority


# ---------------------------------------------------------------------------
# Static sections
# ---------------------------------------------------------------------------

_HEADER = """\
You are Tarka's intelligent planning layer.

Your job is NOT to answer questions directly.
Your job is to decide HOW a question should be answered.

Analyse every user request and produce a structured JSON execution plan.\
"""

_CORE_RULES = """\
## Core Planning Rules

1. ALWAYS prefer a registered tool over answering from your own memory.
2. NEVER use % as modulo when the intent is a percentage.
   Convert instead:  "15% of 340"  ->  "340 * (15 / 100)"
3. For multi-step requests, include every required tool in the plan array.
4. Use "fallback: true" ONLY when absolutely no tool is applicable.
5. Normalize ALL natural language before passing it to the calculator.
6. Be deterministic — identical requests must produce identical plans.\
"""

_NORMALIZATION_RULES = """\
## Expression Normalization Rules

When preparing calculator inputs, apply these transformations:

  Natural Language                 Normalized Expression
  -------------------------------- -----------------------------
  15% of 340                       340 * (15 / 100)
  20 percent of 500                500 * (20 / 100)
  half of 98                       98 / 2
  a third of 60                    60 / 3
  quarter of 80                    80 / 4
  square root of 81                sqrt(81)
  2 raised to the power 8          2 ^ 8
  2 to the power of 8              2 ^ 8
  three plus four                  3 + 4
  ten divided by two               10 / 2
  six times seven                  6 * 7

NEVER pass raw natural language into the calculator.
ALWAYS normalize before including the expression parameter.\
"""

_MULTI_TOOL_GUIDANCE = """\
## Multi-Tool Planning

When a request requires multiple steps, list every step in the plan array.

Example — "Weather in Tokyo and convert to Fahrenheit":

  {
    "plan": [
      {
        "step": 1,
        "tool": "weather",
        "parameters": { "location": "Tokyo" },
        "reason": "Retrieve current temperature in Tokyo"
      },
      {
        "step": 2,
        "tool": "calculator",
        "parameters": { "expression": "(WEATHER_TEMP_C * 9/5) + 32" },
        "reason": "Convert Celsius to Fahrenheit"
      }
    ],
    "fallback": false,
    "reasoning": "Weather lookup followed by unit conversion."
  }

Use a placeholder like WEATHER_TEMP_C when step 2 depends on step 1.
The runtime substitutes real values between steps.\
"""

_OUTPUT_FORMAT = """\
## Required Output Format

Respond with ONLY a JSON object — no prose, no markdown outside the block.

When tools are required:

  {
    "plan": [
      {
        "step": 1,
        "tool": "<registered_tool_name>",
        "parameters": { "<key>": "<value>" },
        "reason": "<why this tool>"
      }
    ],
    "fallback": false,
    "reasoning": "<overall plan explanation>"
  }

When NO tool is required:

  {
    "plan": [],
    "fallback": true,
    "reasoning": "<why no tool is needed>"
  }

Constraints:
  - "tool" must exactly match a registered tool name (see Available Tools).
  - "parameters" must include all required fields for the chosen tool.
  - "fallback: true" means the LLM answers directly without tools.
  - "fallback: false" requires at least one step in "plan".\
"""


# ---------------------------------------------------------------------------
# Dynamic section builders
# ---------------------------------------------------------------------------

def _build_tool_section() -> str:
    tools = get_tools_sorted_by_priority()
    lines: list[str] = ["## Available Tools\n"]

    for tool in tools:
        lines.append(f"### {tool['display_name']}  (tool name: `{tool['name']}`)")
        lines.append(f"**Description:** {tool['description']}\n")

        lines.append("**Use when:**")
        for cond in tool["use_when"]:
            lines.append(f"  - {cond}")

        lines.append("\n**Do NOT use when:**")
        for cond in tool["do_not_use_when"]:
            lines.append(f"  - {cond}")

        lines.append("\n**Parameters:**")
        for pname, pinfo in tool["parameters"].items():
            req_tag = "(required)" if pinfo.get("required") else "(optional)"
            lines.append(f"  - `{pname}` {req_tag} [{pinfo['type']}]: {pinfo['description']}")
            if "examples" in pinfo:
                ex = ", ".join(f'"{e}"' for e in pinfo["examples"][:3])
                lines.append(f"    Examples: {ex}")

        lines.append("")  # blank line between tools

    return "\n".join(lines)


def _build_priority_section() -> str:
    tools = get_tools_sorted_by_priority()
    lines: list[str] = ["## Tool Routing Priority\n"]
    lines.append("When multiple tools could apply, prefer in this order:\n")

    for t in tools:
        lines.append(f"  {t['priority']}. **{t['display_name']}** — {t['description']}")

    llm_pos = len(tools) + 1
    lines.append(f"  {llm_pos}. **LLM Response** — Only when none of the above apply.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_planner_system_prompt() -> str:
    """
    Generate the complete planner system prompt.

    Called fresh on each planning request so it always reflects
    the current state of the tool registry.
    """
    sections = [
        _HEADER,
        "",
        _CORE_RULES,
        "",
        _build_tool_section(),
        "",
        _build_priority_section(),
        "",
        _NORMALIZATION_RULES,
        "",
        _MULTI_TOOL_GUIDANCE,
        "",
        _OUTPUT_FORMAT,
    ]
    return "\n".join(sections)
