"""Filesystem helpers used by document workflows."""

from pathlib import Path


def ensure_directory(path: Path) -> Path:
    """Create a directory when it does not already exist."""
    path.mkdir(parents=True, exist_ok=True)
    return path
