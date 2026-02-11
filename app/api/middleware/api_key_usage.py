"""Middleware for persisting API-key request usage after responses are generated."""

import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.api_key_service import ApiKeyService

logger = logging.getLogger(__name__)


class ApiKeyUsageMiddleware(BaseHTTPMiddleware):
    """Write usage logs for API-key-authenticated requests."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        principal = getattr(request.state, "api_key_principal", None)
        if principal is None:
            return response

        route = request.scope.get("route")
        route_path = getattr(route, "path", request.url.path)
        try:
            await ApiKeyService().log_usage(
                principal=principal,
                method=request.method,
                path=route_path,
                status_code=response.status_code,
                rate_limited=bool(getattr(request.state, "api_key_rate_limited", False)),
                request_id=getattr(request.state, "request_id", None),
                correlation_id=getattr(request.state, "correlation_id", None),
            )
        except Exception:
            logger.exception(
                "failed to persist api key usage log",
                extra={"event": "api_key.usage_log_failed"},
            )

        return response
