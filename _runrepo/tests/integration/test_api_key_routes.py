"""Integration tests for internal API-key management routes."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import app.services.api_key_service as api_key_service_module
from app.dtos.api_key import (
    ApiKeyListResponse,
    ApiKeyResponse,
    ApiKeySecretResponse,
    ApiKeyUsageListResponse,
    ApiKeyUsageResponse,
)

pytestmark = pytest.mark.integration


def test_admin_api_key_routes_return_service_payloads(
    monkeypatch,
    authenticated_client: TestClient,
    authenticated_membership,
) -> None:
    """Admin API-key routes should proxy the expected service payloads."""
    organization_id = authenticated_membership.organization_id
    api_key_id = uuid4()
    issued_at = datetime(2026, 2, 1, 9, 0, tzinfo=timezone.utc)

    async def fake_list_api_keys(self, *, organization_id):
        assert organization_id == authenticated_membership.organization_id
        return ApiKeyListResponse(
            items=[
                ApiKeyResponse(
                    id=api_key_id,
                    organization_id=organization_id,
                    name="Primary integration key",
                    key_prefix="lgk_primary",
                    scopes=["documents:generate", "documents:read"],
                    status="active",
                    rotated_at=None,
                    last_used_at=None,
                    revoked_at=None,
                    created_at=issued_at,
                )
            ]
        )

    async def fake_create_api_key(self, payload, *, current_user_id):
        assert payload.organization_id == organization_id
        assert payload.scopes == ["documents:generate", "documents:read"]
        assert current_user_id == authenticated_membership.user_id
        return ApiKeySecretResponse(
            api_key="lgk_created_secret",
            metadata=ApiKeyResponse(
                id=api_key_id,
                organization_id=organization_id,
                name=payload.name,
                key_prefix="lgk_created",
                scopes=payload.scopes,
                status="active",
                rotated_at=None,
                last_used_at=None,
                revoked_at=None,
                created_at=issued_at,
            ),
        )

    async def fake_rotate_api_key(self, *, organization_id, api_key_id, current_user_id):
        assert organization_id == authenticated_membership.organization_id
        assert api_key_id is not None
        assert current_user_id == authenticated_membership.user_id
        return ApiKeySecretResponse(
            api_key="lgk_rotated_secret",
            metadata=ApiKeyResponse(
                id=api_key_id,
                organization_id=organization_id,
                name="Primary integration key",
                key_prefix="lgk_rotated",
                scopes=["documents:generate", "documents:read"],
                status="active",
                rotated_at=issued_at,
                last_used_at=None,
                revoked_at=None,
                created_at=issued_at,
            ),
        )

    async def fake_revoke_api_key(self, *, organization_id, api_key_id, current_user_id):
        assert organization_id == authenticated_membership.organization_id
        assert api_key_id is not None
        assert current_user_id == authenticated_membership.user_id
        return ApiKeyResponse(
            id=api_key_id,
            organization_id=organization_id,
            name="Primary integration key",
            key_prefix="lgk_rotated",
            scopes=["documents:generate", "documents:read"],
            status="revoked",
            rotated_at=issued_at,
            last_used_at=None,
            revoked_at=issued_at,
            created_at=issued_at,
        )

    async def fake_list_usage_logs(self, *, organization_id, api_key_id, limit):
        assert organization_id == authenticated_membership.organization_id
        assert api_key_id is None
        assert limit == 10
        return ApiKeyUsageListResponse(
            items=[
                ApiKeyUsageResponse(
                    id=uuid4(),
                    api_key_id=uuid4(),
                    organization_id=organization_id,
                    scope="documents:generate",
                    method="POST",
                    path="/api/v1/public/documents/generate",
                    status_code=202,
                    request_id="req-123",
                    correlation_id="corr-123",
                    rate_limited=False,
                    created_at=issued_at,
                )
            ]
        )

    monkeypatch.setattr(api_key_service_module.ApiKeyService, "list_api_keys", fake_list_api_keys)
    monkeypatch.setattr(api_key_service_module.ApiKeyService, "create_api_key", fake_create_api_key)
    monkeypatch.setattr(api_key_service_module.ApiKeyService, "rotate_api_key", fake_rotate_api_key)
    monkeypatch.setattr(api_key_service_module.ApiKeyService, "revoke_api_key", fake_revoke_api_key)
    monkeypatch.setattr(
        api_key_service_module.ApiKeyService,
        "list_usage_logs",
        fake_list_usage_logs,
    )

    list_response = authenticated_client.get(
        "/api/v1/admin/api-keys",
        params={"organization_id": str(organization_id)},
    )
    create_response = authenticated_client.post(
        "/api/v1/admin/api-keys",
        json={
            "organization_id": str(organization_id),
            "name": "Primary integration key",
            "scopes": ["documents:generate", "documents:read"],
        },
    )
    rotate_response = authenticated_client.post(
        f"/api/v1/admin/api-keys/{api_key_id}/rotate",
        params={"organization_id": str(organization_id)},
    )
    revoke_response = authenticated_client.post(
        f"/api/v1/admin/api-keys/{api_key_id}/revoke",
        params={"organization_id": str(organization_id)},
    )
    usage_response = authenticated_client.get(
        "/api/v1/admin/api-keys/usage",
        params={"organization_id": str(organization_id), "limit": 10},
    )

    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["key_prefix"] == "lgk_primary"
    assert create_response.status_code == 201
    assert create_response.json()["api_key"] == "lgk_created_secret"
    assert rotate_response.status_code == 200
    assert rotate_response.json()["metadata"]["key_prefix"] == "lgk_rotated"
    assert revoke_response.status_code == 200
    assert revoke_response.json()["status"] == "revoked"
    assert usage_response.status_code == 200
    assert usage_response.json()["items"][0]["request_id"] == "req-123"
