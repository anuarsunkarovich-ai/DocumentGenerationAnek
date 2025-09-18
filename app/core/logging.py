"""Logging helpers for the backend."""

import logging

from app.core.config import get_settings


def configure_logging() -> None:
    """Configure a minimal logging setup for the application."""
    settings = get_settings()
    logging.basicConfig(
        level=logging.DEBUG if settings.app.debug else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
