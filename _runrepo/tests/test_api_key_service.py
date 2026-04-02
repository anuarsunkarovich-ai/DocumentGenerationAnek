"""Tests for API-key rate limiting and quota enforcement."""

import asyncio
from uuid import uuid4

import pytest

from app.core.exceptions import TooManyRequestsError
from app.dtos.api_key import ApiKeyScope
from app.services.api_key_service import ApiKeyPrincipal, ApiKeyService


class FakeRedisClient:
    """Minimal Redis counter stub for API-key quota tests."""

    def __init__(self) -> None:
        self.counters: dict[str, int] = {}
        self.expirations: dict[str, int] = {}

    def incr(self, key: str) -> int:
        self.counters[key] = self.counters.get(key, 0) + 1
        return self.counters[key]

    def expire(self, key: str, ttl_seconds: int) -> bool:
        self.expirations[key] = ttl_seconds
        return True


def build_principal(*, organization_id=None, api_key_id=None) -> ApiKeyPrincipal:
    """Build a test API-key principal for limit enforcement."""
    return ApiKeyPrincipal(
        api_key_id=api_key_id or uuid4(),
        organization_id=organization_id or uuid4(),
        scopes=(ApiKeyScope.DOCUMENTS_READ,),
        key_prefix="lgk_test",
        scope=ApiKeyScope.DOCUMENTS_READ,
    )


def test_enforce_limits_tracks_per_key_and_per_org_counters(monkeypatch) -> None:
    """Limit enforcement should increment both key and organization buckets."""
    service = ApiKeyService()
    fake_redis = FakeRedisClient()
    principal = build_principal()

    monkeypatch.setattr(service, "_get_redis_client", lambda: fake_redis)
    monkeypatch.setattr(service._settings.api_keys, "requests_per_minute_per_key", 5)
    monkeypatch.setattr(service._settings.api_keys, "requests_per_minute_per_org", 5)
    monkeypatch.setattr(service._settings.api_keys, "requests_per_day_per_key", 5)
    monkeypatch.setattr(service._settings.api_keys, "requests_per_day_per_org", 5)

    asyncio.run(service.enforce_limits(principal))

    assert len(fake_redis.counters) == 4
    assert all(count == 1 for count in fake_redis.counters.values())
    assert len(fake_redis.expirations) == 4


def test_enforce_limits_rejects_when_key_quota_is_exceeded(monkeypatch) -> None:
    """Per-key limits should reject requests after the configured threshold."""
    service = ApiKeyService()
    fake_redis = FakeRedisClient()
    principal = build_principal()

    monkeypatch.setattr(service, "_get_redis_client", lambda: fake_redis)
    monkeypatch.setattr(service._settings.api_keys, "requests_per_minute_per_key", 1)
    monkeypatch.setattr(service._settings.api_keys, "requests_per_minute_per_org", 10)
    monkeypatch.setattr(service._settings.api_keys, "requests_per_day_per_key", 10)
    monkeypatch.setattr(service._settings.api_keys, "requests_per_day_per_org", 10)

    asyncio.run(service.enforce_limits(principal))

    with pytest.raises(TooManyRequestsError, match="API key rate limit exceeded."):
        asyncio.run(service.enforce_limits(principal))


def test_enforce_limits_rejects_when_org_quota_is_exceeded(monkeypatch) -> None:
    """Per-organization quotas should apply across multiple keys in the same tenant."""
    service = ApiKeyService()
    fake_redis = FakeRedisClient()
    organization_id = uuid4()
    first_principal = build_principal(organization_id=organization_id, api_key_id=uuid4())
    second_principal = build_principal(organization_id=organization_id, api_key_id=uuid4())

    monkeypatch.setattr(service, "_get_redis_client", lambda: fake_redis)
    monkeypatch.setattr(service._settings.api_keys, "requests_per_minute_per_key", 10)
    monkeypatch.setattr(service._settings.api_keys, "requests_per_minute_per_org", 1)
    monkeypatch.setattr(service._settings.api_keys, "requests_per_day_per_key", 10)
    monkeypatch.setattr(service._settings.api_keys, "requests_per_day_per_org", 10)

    asyncio.run(service.enforce_limits(first_principal))

    with pytest.raises(TooManyRequestsError, match="API key rate limit exceeded."):
        asyncio.run(service.enforce_limits(second_principal))
