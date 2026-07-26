"""
agent/tools/datetime_tool.py
Current date and time information tool.
"""

from datetime import datetime
from typing import Any

from backend.utils.logger import get_logger
from backend.agent.tools.base import BaseTool

logger = get_logger(__name__)


class DateTimeTool(BaseTool):
    """
    Provides current date, time, and related information.
    No external dependencies required.
    """

    @property
    def name(self) -> str:
        return "datetime"

    @property
    def description(self) -> str:
        return "Returns the current date, time, day of the week, and year."

    def execute(self, **kwargs: Any) -> str:
        """
        Return current datetime information.

        Returns:
            Formatted string with current date and time details.
        """
        now = datetime.now()

        result = (
            f"Current date and time information:\n"
            f"  Date:  {now.strftime('%Y-%m-%d')}\n"
            f"  Time:  {now.strftime('%H:%M:%S')}\n"
            f"  Day:   {now.strftime('%A')}\n"
            f"  Month: {now.strftime('%B')}\n"
            f"  Year:  {now.year}\n"
            f"  Full:  {now.strftime('%A, %B %d, %Y at %H:%M:%S')}"
        )

        logger.info("DateTimeTool executed | %s", now.isoformat())
        return result
