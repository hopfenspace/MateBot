"""
MateBot library containing logging helper functionality
"""

import logging
from typing import Optional


def enforce_logger(logger: Optional[logging.Logger] = None) -> logging.Logger:
    """
    Enforce availability of a working logger
    """

    if logger is not None and isinstance(logger, logging.Logger):
        return logger
    elif logger is not None:
        raise TypeError(f"Expected 'logging.Logger', got {type(logger)}")
    log = logging.getLogger(__name__)
    log.warning("No logger specified for function call; using defaults.")
    return log


class NoDebugFilter(logging.Filter):
    """
    Logging filter that filters out any DEBUG message for the specified logger or handler
    """

    def filter(self, record: logging.LogRecord) -> int:
        if super().filter(record):
            return record.levelno > logging.DEBUG
        return True
