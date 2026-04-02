"""DTOs for internal authentication flows."""

from uuid import UUID

from pydantic import Field, field_validator

from app.dtos.common import BaseDTO


class AuthLoginRequest(BaseDTO):
    """Credentials used for email/password login."""

    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=255)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        """Normalize email addresses before lookup."""
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("Email cannot be empty.")
        return normalized


class AuthRefreshRequest(BaseDTO):
    """Payload for rotating an existing refresh token."""

    refresh_token: str = Field(min_length=20, max_length=500)


class AuthLogoutRequest(BaseDTO):
    """Payload for revoking a refresh token."""

    refresh_token: str = Field(min_length=20, max_length=500)


class AuthOrganizationResponse(BaseDTO):
    """Public organization summary returned with authenticated users."""

    id: UUID
    name: str
    code: str


class AuthMembershipResponse(BaseDTO):
    """Public membership summary returned with authenticated users."""

    id: UUID
    organization_id: UUID
    role: str
    is_active: bool
    is_default: bool
    organization: AuthOrganizationResponse


class AuthUserResponse(BaseDTO):
    """Public identity payload for the authenticated user."""

    id: UUID
    organization_id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    organization: AuthOrganizationResponse
    memberships: list[AuthMembershipResponse] = Field(default_factory=list)


class AuthTokenResponse(BaseDTO):
    """Access and refresh tokens returned to the frontend."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    access_token_expires_in: int
    refresh_token_expires_in: int
    user: AuthUserResponse
