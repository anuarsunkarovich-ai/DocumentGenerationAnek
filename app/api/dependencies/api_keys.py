"""API-key authentication dependencies for public machine routes."""

from collections.abc import Awaitable, Callable

from fastapi import Request

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError, AuthorizationError, TooManyRequestsError
from app.core.request_context import bind_request_state
from app.services.api_key_service import ApiKeyPrincipal, ApiKeyService


def require_api_key_scope(scope: str) -> Callable[[Request], Awaitable[ApiKeyPrincipal]]:
    """Build a dependency that authenticates one API key and enforces one scope."""

    async def dependency(request: Request) -> ApiKeyPrincipal:
        settings = get_settings()
        raw_key = request.headers.get(settings.api_keys.header_name)
        if raw_key is None or not raw_key.strip():
            raise AuthenticationError("API key was not provided.")

        service = ApiKeyService()
        principal = await service.resolve_api_key_principal(
            raw_key=raw_key,
            required_scope=scope,
        )
        request.state.api_key_principal = principal
        request.state.api_key_scope = scope
        request.state.api_key_rate_limited = False
        bind_request_state(
            request,
            organization_id=principal.organization_id,
            api_key_id=principal.api_key_id,
        )

        if not principal.has_scope(scope):
            raise AuthorizationError("API key does not grant the requested scope.")

        try:
            await service.enforce_limits(principal)
        except TooManyRequestsError:
            request.state.api_key_rate_limited = True
            raise

        return principal

    return dependency
