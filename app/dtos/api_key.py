"""DTOs for API-key management and public machine auth."""

from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from app.dtos.common import BaseDTO


class ApiKeyScope:
    """Supported API-key scopes."""

    TEMPLATES_READ = "templates:read"
    DOCUMENTS_GENERATE = "documents:generate"
    DOCUMENTS_READ = "documents:read"
    AUDIT_READ = "audit:read"

    ALL = {
        TEMPLATES_READ,
        DOCUMENTS_GENERATE,
        DOCUMENTS_READ,
        AUDIT_READ,
    }


class ApiKeyCreateRequest(BaseDTO):
    """Payload for creating a new API key."""

    organization_id: UUID
    name: str = Field(min_length=1, max_length=255)
    scopes: list[str] = Field(default_factory=list, min_length=1)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        """Trim key names before persistence."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("Name cannot be empty.")
        return normalized

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, value: list[str]) -> list[str]:
        """Ensure API-key scopes stay within the supported set."""
        normalized = sorted({item.strip() for item in value if item.strip()})
        if not normalized:
            raise ValueError("At least one API-key scope is required.")
        invalid = [item for item in normalized if item not in ApiKeyScope.ALL]
        if invalid:
            raise ValueError(f"Unsupported API-key scopes: {', '.join(invalid)}.")
        return normalized


class ApiKeyAccessQuery(BaseDTO):
    """Tenant-scoped query for one API-key resource."""

    organization_id: UUID


class ApiKeyResponse(BaseDTO):
    """Public metadata for one API key."""

    id: UUID
    organization_id: UUID
    name: str
    key_prefix: str
    scopes: list[str] = Field(default_factory=list)
    status: str
    rotated_at: datetime | None = None
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime


class ApiKeySecretResponse(BaseDTO):
    """Creation or rotation response that includes the plaintext key once."""

    api_key: str
    metadata: ApiKeyResponse


class ApiKeyListResponse(BaseDTO):
    """List of API keys for one organization."""

    items: list[ApiKeyResponse] = Field(default_factory=list)


class ApiKeyUsageQuery(BaseDTO):
    """Tenant-scoped query for recent API-key usage."""

    organization_id: UUID
    api_key_id: UUID | None = None
    limit: int = Field(default=25, ge=1, le=100)


class ApiKeyUsageResponse(BaseDTO):
    """Summarized usage record for one API-key request."""

    id: UUID
    api_key_id: UUID
    organization_id: UUID
    scope: str | None = None
    method: str
    path: str
    status_code: int
    request_id: str | None = None
    correlation_id: str | None = None
    rate_limited: bool
    created_at: datetime


class ApiKeyUsageListResponse(BaseDTO):
    """List of usage records for API-key traffic."""

    items: list[ApiKeyUsageResponse] = Field(default_factory=list)
