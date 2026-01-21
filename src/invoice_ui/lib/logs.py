"""
Logging utilities for the Invoice Search UI.

Provides a simple logger factory that creates configured Python loggers
with consistent formatting across the application.
"""

import logging
import os
from pathlib import Path

# Default log level from environment or INFO
_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


def logger(name: str) -> logging.Logger:
    """
    Create and configure a logger for the given name.

    If name is a file path (e.g., __file__), extracts the module name
    for cleaner log output.

    Args:
        name: Logger name or __file__ path.

    Returns:
        Configured logging.Logger instance.
    """
    # Convert file paths to module-style names
    if "/" in name or "\\" in name:
        name = Path(name).stem

    log = logging.getLogger(name)

    # Only configure if not already configured
    if not log.handlers:
        log.setLevel(getattr(logging, _LOG_LEVEL, logging.INFO))
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        log.addHandler(handler)

    return log
