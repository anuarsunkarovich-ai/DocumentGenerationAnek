"""Logging helpers for the backend."""

import json
import logging
from datetime import datetime, timezone

from app.core.config import get_settings
from app.core.request_context import get_context


class StructuredJsonFormatter(logging.Formatter):
    """Render logs as newline-delimited JSON with request and job context."""

    _base_record = set(logging.makeLogRecord({}).__dict__.keys())

    def format(self, record: logging.LogRecord) -> str:
        """Format one record as structured JSON."""
        payload: dict[str, object | None] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update(get_context())

        for key, value in record.__dict__.items():
            if key in self._base_record or key.startswith("_"):
                continue
            payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging() -> None:
    """Configure structured JSON logging for the application."""
    settings = get_settings()
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredJsonFormatter())
    logging.basicConfig(
        level=logging.DEBUG if settings.app.debug else logging.INFO,
        handlers=[handler],
        force=True,
    )
