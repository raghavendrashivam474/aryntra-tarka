"""
tool_metadata.py
================
Single source of truth for every tool the planner knows about.

Rules:
- Never hardcode tool knowledge in the planner prompt itself.
- All tool descriptions, parameters, and routing hints live here.
- The prompt builder and planner both read from this module.
"""

from __future__ import annotations
from typing import Any


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

TOOL_METADATA: dict[str, dict[str, Any]] = {

    "calculator": {
        "name":         "calculator",
        "display_name": "Calculator",
        "description":  "Evaluates arithmetic and mathematical expressions.",
        "use_when": [
            "The user asks for any mathematical computation",
            "The request contains numbers combined with arithmetic intent",
            "Percentage, fraction, power, or root calculations are needed",
            "Unit conversions that require arithmetic (e.g. Celsius to Fahrenheit)",
        ],
        "do_not_use_when": [
            "The question is conceptual — asking how math works, not for a result",
            "No actual numeric computation is required",
        ],
        "parameters": {
            "expression": {
                "type":        "string",
                "required":    True,
                "description": (
                    "A valid mathematical expression using standard operators: "
                    "+ - * / ^ sqrt() ( ). "
                    "NEVER use % for percentage — convert to (n / 100). "
                    "NEVER pass raw natural language — normalize first."
                ),
                "examples": [
                    "340 * (15 / 100)",
                    "sqrt(81)",
                    "2 ^ 8",
                    "98 / 2",
                    "(0 * 9/5) + 32",
                ],
            },
        },
        "priority": 1,
    },

    "datetime": {
        "name":         "datetime",
        "display_name": "Date & Time",
        "description":  "Returns the current local date, time, or both.",
        "use_when": [
            "The user asks what time it is right now",
            "The user asks what today's date is",
            "The user asks for the current day, month, or year",
        ],
        "do_not_use_when": [
            "The user asks about a historical date or event",
            "The user asks about future scheduling or calendar planning",
        ],
        "parameters": {
            "format": {
                "type":        "string",
                "required":    True,
                "description": "One of: 'date', 'time', 'datetime'",
                "examples":    ["date", "time", "datetime"],
            },
        },
        "priority": 2,
    },

    "weather": {
        "name":         "weather",
        "display_name": "Weather",
        "description":  "Retrieves current weather conditions for any location.",
        "use_when": [
            "The user asks about current weather, temperature, humidity, or wind",
            "A specific location is mentioned with weather intent",
            "The user asks if it is raining, sunny, cold, or hot somewhere",
        ],
        "do_not_use_when": [
            "The user asks about historical weather patterns or climate science",
            "The user asks how weather prediction works conceptually",
        ],
        "parameters": {
            "location": {
                "type":        "string",
                "required":    True,
                "description": "City name or location string.",
                "examples":    ["Tokyo", "London", "New York", "Sydney"],
            },
        },
        "priority": 3,
    },

    "search": {
        "name":         "search",
        "display_name": "Web Search",
        "description":  "Searches the web for current, real-time information.",
        "use_when": [
            "The user asks about recent news or current events",
            "The information may have changed after the model training cutoff",
            "The user asks about live prices, scores, or rankings",
            "The user explicitly asks to search the web",
        ],
        "do_not_use_when": [
            "The question is clearly stable general knowledge",
            "The answer does not depend on recency at all",
        ],
        "parameters": {
            "query": {
                "type":        "string",
                "required":    True,
                "description": "A clear, concise search query optimized for web search.",
                "examples": [
                    "latest AI news 2025",
                    "Bitcoin price today",
                    "Premier League standings",
                ],
            },
        },
        "priority": 4,
    },

    "filesystem": {
        "name":         "filesystem",
        "display_name": "File System",
        "description":  "Reads, writes, lists, or deletes local files and directories.",
        "use_when": [
            "The user asks to read a file",
            "The user asks to write or save content to a file",
            "The user asks to list files in a directory",
            "The user asks to delete or rename a file",
        ],
        "do_not_use_when": [
            "The user is discussing files conceptually without an actual operation",
        ],
        "parameters": {
            "operation": {
                "type":        "string",
                "required":    True,
                "description": "One of: 'read', 'write', 'list', 'delete'",
                "examples":    ["read", "write", "list", "delete"],
            },
            "path": {
                "type":        "string",
                "required":    True,
                "description": "Absolute or relative file or directory path.",
                "examples":    ["/home/user/notes.txt", "C:\\Users\\user\\docs"],
            },
            "content": {
                "type":        "string",
                "required":    False,
                "description": "Content to write. Required only for 'write' operations.",
                "examples":    ["Hello, world!"],
            },
        },
        "priority": 5,
    },

    "clipboard": {
        "name":         "clipboard",
        "display_name": "Clipboard",
        "description":  "Reads from or writes to the system clipboard.",
        "use_when": [
            "The user asks to copy something to their clipboard",
            "The user asks what is currently on the clipboard",
        ],
        "do_not_use_when": [
            "The user is asking about clipboard functionality conceptually",
        ],
        "parameters": {
            "operation": {
                "type":        "string",
                "required":    True,
                "description": "One of: 'read', 'write'",
                "examples":    ["read", "write"],
            },
            "content": {
                "type":        "string",
                "required":    False,
                "description": "Content to write to clipboard. Required only for 'write'.",
                "examples":    ["Text to copy"],
            },
        },
        "priority": 6,
    },

    "password_generator": {
        "name":         "password_generator",
        "display_name": "Password Generator",
        "description":  "Generates a cryptographically secure random password.",
        "use_when": [
            "The user asks for a password to be generated",
            "The user asks for a secure, random, or strong string",
        ],
        "do_not_use_when": [
            "The user asks how passwords work or how to create one manually",
        ],
        "parameters": {
            "length": {
                "type":        "integer",
                "required":    False,
                "description": "Password length. Defaults to 16 if not specified.",
                "examples":    [16, 24, 32],
            },
            "include_symbols": {
                "type":        "boolean",
                "required":    False,
                "description": "Include special characters. Defaults to true.",
                "examples":    [True, False],
            },
        },
        "priority": 7,
    },

    "system_info": {
        "name":         "system_info",
        "display_name": "System Information",
        "description":  "Returns information about the local system hardware and OS.",
        "use_when": [
            "The user asks about CPU, RAM, disk space, or operating system",
            "The user asks about system performance or hardware specifications",
        ],
        "do_not_use_when": [
            "The user asks about system information conceptually",
            "The user is asking about a different machine or hypothetical system",
        ],
        "parameters": {
            "category": {
                "type":        "string",
                "required":    False,
                "description": "One of: 'cpu', 'memory', 'disk', 'os', 'all'. Defaults to 'all'.",
                "examples":    ["cpu", "memory", "disk", "os", "all"],
            },
        },
        "priority": 8,
    },

}


# ---------------------------------------------------------------------------
# Accessors
# ---------------------------------------------------------------------------

def get_tool_metadata(tool_name: str) -> dict[str, Any] | None:
    """Return metadata for a single tool, or None if not registered."""
    return TOOL_METADATA.get(tool_name)


def get_all_tool_metadata() -> dict[str, dict[str, Any]]:
    """Return the full tool registry."""
    return TOOL_METADATA


def get_tools_sorted_by_priority() -> list[dict[str, Any]]:
    """Return all tools ordered by ascending routing priority."""
    return sorted(TOOL_METADATA.values(), key=lambda t: t["priority"])


def is_registered_tool(tool_name: str) -> bool:
    """Return True if the tool name exists in the registry."""
    return tool_name in TOOL_METADATA
