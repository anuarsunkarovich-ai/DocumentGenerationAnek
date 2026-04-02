"""Internal admin routes for API-key management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from app.api.controllers.api_key_controller import ApiKeyController
from app.api.dependencies.auth import get_current_user
from app.api.dependencies.authorization import require_audit_access
from app.dtos.api_key import (
    ApiKeyAccessQuery,
    ApiKeyCreateRequest,
    ApiKeyListResponse,
    ApiKeyResponse,
    ApiKeySecretResponse,
    ApiKeyUsageListResponse,
    ApiKeyUsageQuery,
)
from app.models.user import User
from app.services.api_key_service import ApiKeyService

router = APIRouter(prefix="/admin/api-keys", tags=["api-keys"])


@router.get("", response_model=ApiKeyListResponse)
async def list_api_keys(
    request: Request,
    query: Annotated[ApiKeyAccessQuery, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApiKeyListResponse:
    """Return API keys for the selected organization."""
    require_audit_access(current_user, query.organization_id, request=request)
    controller = ApiKeyController(service=ApiKeyService())
    return await controller.list_api_keys(organization_id=query.organization_id)


@router.post("", response_model=ApiKeySecretResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: Request,
    payload: ApiKeyCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApiKeySecretResponse:
    """Create one API key for the selected organization."""
    membership = require_audit_access(current_user, payload.organization_id, request=request)
    controller = ApiKeyController(service=ApiKeyService())
    return await controller.create_api_key(payload, current_user_id=membership.user_id)


@router.post("/{api_key_id}/rotate", response_model=ApiKeySecretResponse)
async def rotate_api_key(
    request: Request,
    api_key_id: UUID,
    query: Annotated[ApiKeyAccessQuery, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApiKeySecretResponse:
    """Rotate one API key and return the replacement plaintext key."""
    membership = require_audit_access(current_user, query.organization_id, request=request)
    controller = ApiKeyController(service=ApiKeyService())
    return await controller.rotate_api_key(
        organization_id=query.organization_id,
        api_key_id=api_key_id,
        current_user_id=membership.user_id,
    )


@router.post("/{api_key_id}/revoke", response_model=ApiKeyResponse)
async def revoke_api_key(
    request: Request,
    api_key_id: UUID,
    query: Annotated[ApiKeyAccessQuery, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApiKeyResponse:
    """Revoke one API key."""
    membership = require_audit_access(current_user, query.organization_id, request=request)
    controller = ApiKeyController(service=ApiKeyService())
    return await controller.revoke_api_key(
        organization_id=query.organization_id,
        api_key_id=api_key_id,
        current_user_id=membership.user_id,
    )


@router.get("/usage", response_model=ApiKeyUsageListResponse)
async def list_api_key_usage(
    request: Request,
    query: Annotated[ApiKeyUsageQuery, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApiKeyUsageListResponse:
    """Return recent API-key usage logs."""
    require_audit_access(current_user, query.organization_id, request=request)
    controller = ApiKeyController(service=ApiKeyService())
    return await controller.list_usage_logs(
        organization_id=query.organization_id,
        api_key_id=query.api_key_id,
        limit=query.limit,
    )
