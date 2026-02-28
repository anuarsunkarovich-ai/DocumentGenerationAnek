"""API-key management, authentication, and usage helpers."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import cast
from uuid import UUID

from redis import Redis

from app.core.auth import api_key_prefix, generate_api_key, hash_api_key
from app.core.config import get_settings
from app.core.database import get_transaction_session
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    TooManyRequestsError,
)
from app.dtos.api_key import (
    ApiKeyCreateRequest,
    ApiKeyListResponse,
    ApiKeyResponse,
    ApiKeySecretResponse,
    ApiKeyUsageListResponse,
    ApiKeyUsageResponse,
)
from app.models.api_key import ApiKey
from app.models.api_key_usage_log import ApiKeyUsageLog
from app.models.enums import AuditAction
from app.repositories.api_key_repository import ApiKeyRepository
from app.repositories.api_key_usage_log_repository import ApiKeyUsageLogRepository
from app.repositories.organization_repository import OrganizationRepository
from app.services.audit_service import AuditService


@dataclass(frozen=True)
class ApiKeyPrincipal:
    """Authenticated machine principal derived from one API key."""

    api_key_id: UUID
    organization_id: UUID
    scopes: tuple[str, ...]
    key_prefix: str
    scope: str

    def has_scope(self, scope: str) -> bool:
        """Return whether the principal contains the requested scope."""
        return scope in self.scopes


class ApiKeyService:
    """Manage API keys and authenticate machine-to-machine requests."""

    def __init__(self) -> None:
        """Cache shared settings for API-key operations."""
        self._settings = get_settings()

    async def create_api_key(
        self,
        payload: ApiKeyCreateRequest,
        *,
        current_user_id: UUID,
    ) -> ApiKeySecretResponse:
        """Create one API key and return the plaintext secret once."""
        plaintext_key = generate_api_key()
        prefix = api_key_prefix(plaintext_key)
        hashed_key = hash_api_key(plaintext_key)

        async with get_transaction_session() as session:
            organization = await OrganizationRepository(session).get_by_id(payload.organization_id)
            if organization is None:
                raise NotFoundError("Organization was not found.")

            repository = ApiKeyRepository(session)
            audit_service = AuditService(session)
            api_key = await repository.create(
                ApiKey(
                    organization_id=payload.organization_id,
                    name=payload.name,
                    key_prefix=prefix,
                    hashed_key=hashed_key,
                    scopes=payload.scopes,
                    status="active",
                )
            )
            await audit_service.log_event(
                organization_id=payload.organization_id,
                user_id=current_user_id,
                action=AuditAction.API_KEY_CREATED,
                entity_type="api_key",
                entity_id=api_key.id,
                payload={
                    "name": api_key.name,
                    "key_prefix": api_key.key_prefix,
                    "scopes": api_key.scopes,
                },
            )
            return ApiKeySecretResponse(
                api_key=plaintext_key,
                metadata=self._serialize_api_key(api_key),
            )

    async def list_api_keys(self, *, organization_id: UUID) -> ApiKeyListResponse:
        """Return API keys for one organization."""
        async with get_transaction_session() as session:
            items = await ApiKeyRepository(session).list_for_organization(organization_id)
            return ApiKeyListResponse(items=[self._serialize_api_key(item) for item in items])

    async def rotate_api_key(
        self,
        *,
        organization_id: UUID,
        api_key_id: UUID,
        current_user_id: UUID,
    ) -> ApiKeySecretResponse:
        """Rotate one API key and return the replacement plaintext key."""
        plaintext_key = generate_api_key()
        prefix = api_key_prefix(plaintext_key)
        hashed_key = hash_api_key(plaintext_key)

        async with get_transaction_session() as session:
            repository = ApiKeyRepository(session)
            audit_service = AuditService(session)
            api_key = await repository.get_by_id(api_key_id, organization_id=organization_id)
            if api_key is None:
                raise NotFoundError("API key was not found.")

            api_key = await repository.rotate(
                api_key,
                key_prefix=prefix,
                hashed_key=hashed_key,
            )
            await audit_service.log_event(
                organization_id=organization_id,
                user_id=current_user_id,
                action=AuditAction.API_KEY_ROTATED,
                entity_type="api_key",
                entity_id=api_key.id,
                payload={
                    "name": api_key.name,
                    "key_prefix": api_key.key_prefix,
                    "scopes": api_key.scopes,
                },
            )
            return ApiKeySecretResponse(
                api_key=plaintext_key,
                metadata=self._serialize_api_key(api_key),
            )

    async def revoke_api_key(
        self,
        *,
        organization_id: UUID,
        api_key_id: UUID,
        current_user_id: UUID,
    ) -> ApiKeyResponse:
        """Revoke one API key."""
        async with get_transaction_session() as session:
            repository = ApiKeyRepository(session)
            audit_service = AuditService(session)
            api_key = await repository.get_by_id(api_key_id, organization_id=organization_id)
            if api_key is None:
                raise NotFoundError("API key was not found.")

            api_key = await repository.revoke(api_key)
            await audit_service.log_event(
                organization_id=organization_id,
                user_id=current_user_id,
                action=AuditAction.API_KEY_REVOKED,
                entity_type="api_key",
                entity_id=api_key.id,
                payload={
                    "name": api_key.name,
                    "key_prefix": api_key.key_prefix,
                    "scopes": api_key.scopes,
                },
            )
            return self._serialize_api_key(api_key)

    async def disable_api_key(
        self,
        *,
        organization_id: UUID,
        api_key_id: UUID,
        current_user_id: UUID,
    ) -> ApiKeyResponse:
        """Disable one API key without rotating or revoking it permanently."""
        async with get_transaction_session() as session:
            repository = ApiKeyRepository(session)
            audit_service = AuditService(session)
            api_key = await repository.get_by_id(api_key_id, organization_id=organization_id)
            if api_key is None:
                raise NotFoundError("API key was not found.")

            api_key = await repository.set_status(api_key, status="disabled")
            await audit_service.log_event(
                organization_id=organization_id,
                user_id=current_user_id,
                action=AuditAction.API_KEY_DISABLED,
                entity_type="api_key",
                entity_id=api_key.id,
                payload={
                    "name": api_key.name,
                    "key_prefix": api_key.key_prefix,
                    "scopes": api_key.scopes,
                    "status": api_key.status,
                },
            )
            return self._serialize_api_key(api_key)

    async def resolve_api_key_principal(
        self,
        *,
        raw_key: str,
        required_scope: str,
    ) -> ApiKeyPrincipal:
        """Authenticate one API key and load its machine principal."""
        async with get_transaction_session() as session:
            repository = ApiKeyRepository(session)
            api_key = await repository.get_by_hashed_key(hash_api_key(raw_key.strip()))
            if api_key is None or api_key.status != "active" or api_key.revoked_at is not None:
                raise AuthenticationError("API key is invalid.")
            if api_key.organization is None or not api_key.organization.is_active:
                raise AuthenticationError("API key is invalid.")

            principal = ApiKeyPrincipal(
                api_key_id=api_key.id,
                organization_id=api_key.organization_id,
                scopes=tuple(sorted(api_key.scopes)),
                key_prefix=api_key.key_prefix,
                scope=required_scope,
            )

        return principal

    async def authenticate_api_key(
        self,
        *,
        raw_key: str,
        required_scope: str,
    ) -> ApiKeyPrincipal:
        """Authenticate one API key, validate scope, and enforce limits."""
        principal = await self.resolve_api_key_principal(
            raw_key=raw_key,
            required_scope=required_scope,
        )
        if not principal.has_scope(required_scope):
            raise AuthorizationError("API key does not grant the requested scope.")
        await self.enforce_limits(principal)
        return principal

    async def log_usage(
        self,
        *,
        principal: ApiKeyPrincipal,
        method: str,
        path: str,
        status_code: int,
        rate_limited: bool,
        request_id: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Persist one API-key usage record and touch the key."""
        async with get_transaction_session() as session:
            repository = ApiKeyRepository(session)
            usage_repository = ApiKeyUsageLogRepository(session)
            api_key = await repository.get_by_id(principal.api_key_id)
            if api_key is None:
                return

            await repository.touch(api_key)
            await usage_repository.create(
                ApiKeyUsageLog(
                    api_key_id=principal.api_key_id,
                    organization_id=principal.organization_id,
                    scope=principal.scope,
                    method=method,
                    path=path,
                    status_code=status_code,
                    request_id=request_id,
                    correlation_id=correlation_id,
                    rate_limited=rate_limited,
                )
            )

    async def list_usage_logs(
        self,
        *,
        organization_id: UUID,
        api_key_id: UUID | None,
        limit: int,
    ) -> ApiKeyUsageListResponse:
        """Return recent usage logs for one organization or one API key."""
        async with get_transaction_session() as session:
            usage_logs = await ApiKeyUsageLogRepository(session).list_recent(
                organization_id=organization_id,
                api_key_id=api_key_id,
                limit=limit,
            )
            return ApiKeyUsageListResponse(
                items=[
                    ApiKeyUsageResponse(
                        id=item.id,
                        api_key_id=item.api_key_id,
                        organization_id=item.organization_id,
                        scope=item.scope,
                        method=item.method,
                        path=item.path,
                        status_code=item.status_code,
                        request_id=item.request_id,
                        correlation_id=item.correlation_id,
                        rate_limited=item.rate_limited,
                        created_at=item.created_at,
                    )
                    for item in usage_logs
                ]
            )

    async def enforce_limits(self, principal: ApiKeyPrincipal) -> None:
        """Apply per-key and per-organization rate limits and quotas."""
        now = datetime.now(timezone.utc)
        minute_bucket = now.strftime("%Y%m%d%H%M")
        day_bucket = now.strftime("%Y%m%d")
        minute_ttl = 90
        day_ttl = 60 * 60 * 25

        await self._increment_and_check(
            counter_key=f"api-key:minute:key:{principal.api_key_id}:{minute_bucket}",
            limit=self._settings.api_keys.requests_per_minute_per_key,
            ttl_seconds=minute_ttl,
        )
        await self._increment_and_check(
            counter_key=f"api-key:minute:org:{principal.organization_id}:{minute_bucket}",
            limit=self._settings.api_keys.requests_per_minute_per_org,
            ttl_seconds=minute_ttl,
        )
        await self._increment_and_check(
            counter_key=f"api-key:day:key:{principal.api_key_id}:{day_bucket}",
            limit=self._settings.api_keys.requests_per_day_per_key,
            ttl_seconds=day_ttl,
        )
        await self._increment_and_check(
            counter_key=f"api-key:day:org:{principal.organization_id}:{day_bucket}",
            limit=self._settings.api_keys.requests_per_day_per_org,
            ttl_seconds=day_ttl,
        )

    async def _increment_and_check(
        self,
        *,
        counter_key: str,
        limit: int,
        ttl_seconds: int,
    ) -> None:
        """Increment one Redis counter and enforce its upper bound."""
        if limit <= 0:
            return

        def operation() -> int:
            client = self._get_redis_client()
            current = cast(int, client.incr(counter_key))
            if current == 1:
                client.expire(counter_key, ttl_seconds)
            return current

        current = await asyncio.to_thread(operation)
        if current > limit:
            raise TooManyRequestsError("API key rate limit exceeded.")

    def _get_redis_client(self) -> Redis:
        """Build a Redis client from configured settings."""
        return Redis.from_url(self._settings.redis.broker_url, decode_responses=True)

    def _serialize_api_key(self, api_key: ApiKey) -> ApiKeyResponse:
        """Serialize one API key for API responses."""
        return ApiKeyResponse(
            id=api_key.id,
            organization_id=api_key.organization_id,
            name=api_key.name,
            key_prefix=api_key.key_prefix,
            scopes=sorted(api_key.scopes),
            status=api_key.status,
            rotated_at=api_key.rotated_at,
            last_used_at=api_key.last_used_at,
            revoked_at=api_key.revoked_at,
            created_at=api_key.created_at,
        )
