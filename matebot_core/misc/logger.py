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
