"""Optional error-reporting integrations for API and worker runtimes."""

from typing import Any

from sentry_sdk import init as sentry_init
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration

from app.core.config import get_settings


def configure_error_reporting(*, runtime: str) -> None:
    """Initialize Sentry if a DSN is configured."""
    settings = get_settings()
    dsn = settings.observability.sentry_dsn
    if not dsn:
        return

    integrations: list[Any] = [CeleryIntegration()]
    if runtime == "api":
        integrations.append(FastApiIntegration())

    sentry_init(
        dsn=dsn,
        environment=settings.app.environment,
        release=settings.app.version,
        traces_sample_rate=settings.observability.sentry_traces_sample_rate,
        integrations=integrations,
    )
