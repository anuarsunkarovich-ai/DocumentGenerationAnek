"""Controller helpers for authentication routes."""

from app.dtos.auth import (
    AuthLoginRequest,
    AuthLogoutRequest,
    AuthRefreshRequest,
    AuthTokenResponse,
    AuthUserResponse,
)
from app.models.user import User
from app.services.auth_service import AuthService


class AuthController:
    """Coordinate authentication requests."""

    def __init__(self, service: AuthService) -> None:
        self._service = service

    async def login(self, payload: AuthLoginRequest) -> AuthTokenResponse:
        """Authenticate one user and return a token pair."""
        return await self._service.login(payload)

    async def refresh(self, payload: AuthRefreshRequest) -> AuthTokenResponse:
        """Rotate a refresh token and return a fresh token pair."""
        return await self._service.refresh(payload.refresh_token)

    async def logout(self, payload: AuthLogoutRequest, current_user: User) -> None:
        """Revoke the supplied refresh token for the current user."""
        await self._service.logout(refresh_token=payload.refresh_token, current_user=current_user)

    async def get_me(self, current_user: User) -> AuthUserResponse:
        """Return the authenticated user profile."""
        return self._service.get_me(current_user)
