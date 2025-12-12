"""Request middleware for request IDs, correlation IDs, metrics, and access logs."""

import logging
import time
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.metrics import record_request_metrics
from app.core.request_context import bind_context, clear_context

logger = logging.getLogger(__name__)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Attach request correlation data and record request metrics."""

    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        request_id = request.headers.get(settings.observability.request_id_header) or str(uuid4())
        correlation_id = request.headers.get(settings.observability.correlation_id_header) or request_id
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id
        bind_context(request_id=request_id, correlation_id=correlation_id)

        started_at = time.perf_counter()
        response = None
        try:
            response = await call_next(request)
        finally:
            duration_seconds = time.perf_counter() - started_at
            route = request.scope.get("route")
            route_path = getattr(route, "path", request.url.path)
            status_code = response.status_code if response is not None else 500
            record_request_metrics(
                method=request.method,
                route=route_path,
                status_code=status_code,
                duration_seconds=duration_seconds,
            )
            logger.info(
                "request completed",
                extra={
                    "event": "request.completed",
                    "method": request.method,
                    "path": request.url.path,
                    "route": route_path,
                    "status_code": status_code,
                    "duration_ms": round(duration_seconds * 1000, 2),
                },
            )
            clear_context()

        if response is not None:
            response.headers[settings.observability.request_id_header] = request_id
            response.headers[settings.observability.correlation_id_header] = correlation_id
        return response
