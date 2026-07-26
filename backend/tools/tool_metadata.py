"""
Tool Metadata Schema
Sprint 3.15 - Dynamic Tool Awareness
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional


@dataclass
class ToolParameter:
    name: str
    type: str
    description: str
    required: bool = True
    example: Optional[str] = None


@dataclass
class ToolMetadata:
    name: str
    description: str
    purpose: str
    use_when: List[str]
    do_not_use_when: List[str] = field(default_factory=list)
    parameters: List[ToolParameter] = field(default_factory=list)
    examples: List[Dict[str, str]] = field(default_factory=list)
    priority: int = 50  # Higher = preferred
    category: str = "general"

    def to_prompt_block(self) -> str:
        lines = [f"### {self.name}", f"Purpose: {self.purpose}", ""]
        if self.use_when:
            lines.append("Use When:")
            for u in self.use_when:
                lines.append(f"  - {u}")
        if self.do_not_use_when:
            lines.append("Do Not Use When:")
            for d in self.do_not_use_when:
                lines.append(f"  - {d}")
        if self.parameters:
            lines.append("Parameters:")
            for p in self.parameters:
                req = "required" if p.required else "optional"
                ex = f" (e.g. {p.example})" if p.example else ""
                lines.append(f"  - {p.name} ({p.type}, {req}): {p.description}{ex}")
        if self.examples:
            lines.append("Examples:")
            for ex in self.examples:
                lines.append(f"  - Input: {ex.get('input','')} -> {ex.get('output','')}")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d
