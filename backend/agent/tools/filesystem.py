"""
agent/tools/filesystem.py
Safe read-only filesystem tool.

Lists directory contents within the project working directory.
Write operations are excluded from Sprint 2.
Directory traversal outside the project root is blocked.
"""

from pathlib import Path
from typing import Any

from backend.utils.logger import get_logger
from backend.agent.tools.base import BaseTool, ToolError

logger = get_logger(__name__)

# All operations are restricted to the project working directory
_ROOT = Path.cwd()


class FileSystemTool(BaseTool):
    """
    Read-only filesystem tool.

    Lists files and directories at a given path.
    All paths are resolved relative to the project root.
    """

    @property
    def name(self) -> str:
        return "filesystem"

    @property
    def description(self) -> str:
        return (
            "Lists files and directories. "
            "Accepts an optional 'path' argument (default: current directory)."
        )

    def execute(self, path: str = ".", **kwargs: Any) -> str:
        """
        List the contents of a directory.

        Args:
            path: Directory path relative to project root (default: ".").

        Returns:
            Formatted directory listing as a string.

        Raises:
            ToolError: If path is invalid, missing, or outside project root.
        """
        target = (_ROOT / path).resolve()

        # Security: block directory traversal
        if not str(target).startswith(str(_ROOT)):
            raise ToolError(
                f"Access denied: '{path}' resolves outside project root."
            )

        if not target.exists():
            raise ToolError(f"Path does not exist: '{path}'")

        if not target.is_dir():
            raise ToolError(f"Path is not a directory: '{path}'")

        logger.debug("FileSystemTool listing: %s", target)

        entries = sorted(target.iterdir(), key=lambda e: (e.is_file(), e.name))

        if not entries:
            return f"Directory '{path}' is empty."

        dirs  = [e for e in entries if e.is_dir()]
        files = [e for e in entries if e.is_file()]
        lines = [f"Contents of '{target}':"]

        if dirs:
            lines.append(f"\n  Directories ({len(dirs)}):")
            for d in dirs:
                lines.append(f"    [DIR]  {d.name}/")

        if files:
            lines.append(f"\n  Files ({len(files)}):")
            for f in files:
                size = f.stat().st_size
                lines.append(f"    [FILE] {f.name}  ({size:,} bytes)")

        logger.info(
            "FileSystemTool listed %d items in '%s'", len(entries), path
        )
        return "\n".join(lines)
