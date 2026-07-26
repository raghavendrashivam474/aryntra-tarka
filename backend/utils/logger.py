"""
Centralised logging utility for Aryntra Tarka.

Responsibilities:
- Provide a single configured logger
- Ensure consistent log format across all modules
- Support application, warning, and error logs

Usage:
    from backend.utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Message")
    logger.warning("Warning")
    logger.error("Error")
"""

import logging
import sys


# ---------------------------------------------------------------------------
# Formatter
# ---------------------------------------------------------------------------

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _build_handler() -> logging.StreamHandler:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT))
    return handler


# ---------------------------------------------------------------------------
# Logger Factory
# ---------------------------------------------------------------------------

def get_logger(name: str) -> logging.Logger:
    """
    Returns a configured logger for the given module name.

    Args:
        name: Typically passed as __name__ from the calling module.

    Returns:
        A configured logging.Logger instance.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.addHandler(_build_handler())
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

    return logger
