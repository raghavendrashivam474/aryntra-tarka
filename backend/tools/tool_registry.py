"""
Tool Registry - Sprint 3.15
Dynamic tool discovery with rich metadata.
"""
from typing import Dict, List, Optional
from .tool_metadata import ToolMetadata, ToolParameter


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolMetadata] = {}
        self._register_defaults()

    def register(self, meta: ToolMetadata) -> None:
        self._tools[meta.name.lower()] = meta

    def get(self, name: str) -> Optional[ToolMetadata]:
        return self._tools.get(name.lower())

    def all(self) -> List[ToolMetadata]:
        return sorted(self._tools.values(), key=lambda t: -t.priority)

    def names(self) -> List[str]:
        return [t.name for t in self.all()]

    def to_prompt(self) -> str:
        """Render all tool metadata for planner prompt."""
        blocks = [t.to_prompt_block() for t in self.all()]
        return "\n\n".join(blocks)

    # ---------------------------------------------------------
    def _register_defaults(self):
        self.register(ToolMetadata(
            name="calculator",
            description="Perform arithmetic and mathematical operations.",
            purpose="Perform arithmetic calculations.",
            use_when=[
                "The request contains numbers and mathematical operations.",
                "The user asks for percentages, roots, powers, or arithmetic.",
                "The user writes natural-language math like 'half of 98'.",
            ],
            do_not_use_when=[
                "The question is conceptual (e.g. 'explain recursion').",
            ],
            parameters=[
                ToolParameter("expression", "string", "Valid math expression.",
                              example="340 * (15 / 100)")
            ],
            examples=[
                {"input": "15% of 340", "output": "340 * (15 / 100)"},
                {"input": "square root of 81", "output": "sqrt(81)"},
                {"input": "2 raised to the power 8", "output": "2 ^ 8"},
            ],
            priority=95,
            category="math",
        ))

        self.register(ToolMetadata(
            name="weather",
            description="Retrieve current weather for a location.",
            purpose="Get current weather information.",
            use_when=[
                "The user asks about current weather, temperature, humidity.",
                "The user mentions a city with weather context.",
            ],
            do_not_use_when=[
                "The user asks about historical climate patterns.",
            ],
            parameters=[
                ToolParameter("location", "string", "City or place name.",
                              example="Tokyo")
            ],
            examples=[
                {"input": "Weather in Tokyo", "output": "location=Tokyo"},
            ],
            priority=90,
            category="realtime",
        ))

        self.register(ToolMetadata(
            name="search",
            description="Search the web for current information.",
            purpose="Retrieve up-to-date information from the web.",
            use_when=[
                "The user asks about news, current events, or latest info.",
                "The topic requires knowledge more recent than the model's cutoff.",
            ],
            do_not_use_when=[
                "The user asks a general knowledge or conceptual question.",
            ],
            parameters=[
                ToolParameter("query", "string", "Search query string.",
                              example="latest AI news")
            ],
            priority=85,
            category="realtime",
        ))

        self.register(ToolMetadata(
            name="datetime",
            description="Get current date and time.",
            purpose="Return current date/time or perform date arithmetic.",
            use_when=[
                "The user asks for today's date, current time, or day of week.",
            ],
            parameters=[
                ToolParameter("timezone", "string", "Optional timezone.",
                              required=False, example="UTC")
            ],
            priority=80,
            category="realtime",
        ))

        self.register(ToolMetadata(
            name="filesystem",
            description="Read or list local files.",
            purpose="Interact with the local file system.",
            use_when=[
                "The user asks to read, list, or inspect local files.",
            ],
            parameters=[
                ToolParameter("path", "string", "Absolute or relative path.")
            ],
            priority=75,
            category="system",
        ))

        self.register(ToolMetadata(
            name="clipboard",
            description="Read or write the system clipboard.",
            purpose="Access clipboard contents.",
            use_when=[
                "The user asks to copy, paste, or read clipboard content.",
            ],
            parameters=[
                ToolParameter("action", "string", "read|write"),
                ToolParameter("content", "string", "Content to write.",
                              required=False),
            ],
            priority=70,
            category="system",
        ))

        self.register(ToolMetadata(
            name="password_generator",
            description="Generate secure passwords.",
            purpose="Create strong random passwords.",
            use_when=[
                "The user asks for a password or secure token.",
            ],
            parameters=[
                ToolParameter("length", "int", "Password length.",
                              required=False, example="16"),
                ToolParameter("symbols", "bool", "Include symbols.",
                              required=False, example="true"),
            ],
            priority=65,
            category="utility",
        ))

        self.register(ToolMetadata(
            name="system_info",
            description="Get information about the host system.",
            purpose="Retrieve OS, CPU, memory info.",
            use_when=[
                "The user asks about the machine, OS, CPU, RAM, disk.",
            ],
            parameters=[],
            priority=60,
            category="system",
        ))


# Singleton
_registry: Optional[ToolRegistry] = None

def get_registry() -> ToolRegistry:
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
