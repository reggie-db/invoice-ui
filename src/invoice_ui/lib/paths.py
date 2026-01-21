"""
Path utilities for the Invoice Search UI.

Provides convenience functions for common path operations like
getting temporary directories.
"""

import tempfile
from pathlib import Path


def temp_dir() -> Path:
    """
    Return the system temporary directory as a Path.

    Returns:
        Path object pointing to the system temp directory.
    """
    return Path(tempfile.gettempdir())
