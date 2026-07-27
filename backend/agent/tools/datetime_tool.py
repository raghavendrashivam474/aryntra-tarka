"""
agent/tools/datetime_tool.py
Current date and time information tool.

Sprint 3.16 - Added execute_structured() returning a typed dict so the
              orchestration layer can extract CURRENT_HOUR, CURRENT_MINUTE
              etc. for variable substitution into downstream tool calls.
              execute() is unchanged — backward compatible.
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
        Return current datetime information as a formatted string.
        Unchanged from previous sprints.
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

    def execute_structured(self, **kwargs: Any) -> dict[str, Any]:
        """
        Return current datetime as a structured dictionary.

        Sprint 3.16: used by the orchestration layer for variable
        substitution. Keys map directly to placeholder names.

        Returns:
            {
                "hour":      int,
                "minute":    int,
                "second":    int,
                "date":      str  YYYY-MM-DD,
                "time":      str  HH:MM:SS,
                "day":       str  Monday,
                "month":     str  January,
                "year":      int,
                "formatted": str  full human string,
                "timestamp": str  ISO 8601,
            }
        """
        now = datetime.now()
        structured = {
            "hour":      now.hour,
            "minute":    now.minute,
            "second":    now.second,
            "date":      now.strftime("%Y-%m-%d"),
            "time":      now.strftime("%H:%M:%S"),
            "day":       now.strftime("%A"),
            "month":     now.strftime("%B"),
            "year":      now.year,
            "formatted": now.strftime("%A, %B %d, %Y at %H:%M:%S"),
            "timestamp": now.isoformat(),
        }
        logger.info(
            "DateTimeTool structured | %02d:%02d:%02d",
            now.hour, now.minute, now.second,
        )
        return structured
