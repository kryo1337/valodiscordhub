"""
Logging configuration for the API.
Sets up structured logging with the 'valohub' logger.
"""

import logging
import sys
from datetime import datetime, timezone


class UTCFormatter(logging.Formatter):
    """Formatter that uses UTC timestamps."""

    converter = lambda *args: datetime.now(timezone.utc).timetuple()

    def formatTime(self, record, datefmt=None):
        ct = datetime.now(timezone.utc)
        if datefmt:
            return ct.strftime(datefmt)
        return ct.isoformat()


def setup_logging(level: str = "INFO") -> logging.Logger:
    """
    Set up logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)

    Returns:
        The configured 'valohub' logger
    """
    # Create or get the valohub logger
    logger = logging.getLogger("valohub")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Console handler with structured format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    # Format: timestamp | level | module | message
    formatter = UTCFormatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s.%(funcName)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S.%f",
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Also configure uvicorn loggers to use similar format
    for uvicorn_logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
        uvicorn_logger = logging.getLogger(uvicorn_logger_name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.addHandler(console_handler)

    return logger


def get_logger(name: str = "valohub") -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)
