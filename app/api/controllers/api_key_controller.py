"""Controller helpers for API-key management endpoints."""

from uuid import UUID

from app.dtos.api_key import (
    ApiKeyCreateRequest,
    ApiKeyListResponse,
    ApiKeyResponse,
    ApiKeySecretResponse,
    ApiKeyUsageListResponse,
)
from app.services.api_key_service import ApiKeyService


class ApiKeyController:
    """Coordinate API-key management requests."""

    def __init__(self, service: ApiKeyService) -> None:
        self._service = service

    async def create_api_key(
        self,
        payload: ApiKeyCreateRequest,
        *,
        current_user_id: UUID,
    ) -> ApiKeySecretResponse:
        """Create one API key."""
        return await self._service.create_api_key(payload, current_user_id=current_user_id)

    async def list_api_keys(self, *, organization_id: UUID) -> ApiKeyListResponse:
        """Return API keys for one organization."""
        return await self._service.list_api_keys(organization_id=organization_id)

    async def rotate_api_key(
        self,
        *,
        organization_id: UUID,
        api_key_id: UUID,
        current_user_id: UUID,
    ) -> ApiKeySecretResponse:
        """Rotate one API key."""
        return await self._service.rotate_api_key(
            organization_id=organization_id,
            api_key_id=api_key_id,
            current_user_id=current_user_id,
        )

    async def revoke_api_key(
        self,
        *,
        organization_id: UUID,
        api_key_id: UUID,
        current_user_id: UUID,
    ) -> ApiKeyResponse:
        """Revoke one API key."""
        return await self._service.revoke_api_key(
            organization_id=organization_id,
            api_key_id=api_key_id,
            current_user_id=current_user_id,
        )

    async def list_usage_logs(
        self,
        *,
        organization_id: UUID,
        api_key_id: UUID | None,
        limit: int,
    ) -> ApiKeyUsageListResponse:
        """Return recent usage logs."""
        return await self._service.list_usage_logs(
            organization_id=organization_id,
            api_key_id=api_key_id,
            limit=limit,
        )
