"""Authentication API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.controllers.auth_controller import AuthController
from app.api.dependencies.auth import get_current_user
from app.dtos.auth import (
    AuthLoginRequest,
    AuthLogoutRequest,
    AuthRefreshRequest,
    AuthTokenResponse,
    AuthUserResponse,
)
from app.models.user import User
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/login", response_model=AuthTokenResponse, status_code=status.HTTP_200_OK)
async def login(payload: AuthLoginRequest) -> AuthTokenResponse:
    """Authenticate a user with email and password."""
    controller = AuthController(service=AuthService())
    return await controller.login(payload)


@router.post("/refresh", response_model=AuthTokenResponse, status_code=status.HTTP_200_OK)
async def refresh(payload: AuthRefreshRequest) -> AuthTokenResponse:
    """Rotate a refresh token and issue fresh credentials."""
    controller = AuthController(service=AuthService())
    return await controller.refresh(payload)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: AuthLogoutRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    """Revoke a refresh token for the authenticated user."""
    controller = AuthController(service=AuthService())
    await controller.logout(payload, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=AuthUserResponse, status_code=status.HTTP_200_OK)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> AuthUserResponse:
    """Return the authenticated user profile."""
    controller = AuthController(service=AuthService())
    return await controller.get_me(current_user)
