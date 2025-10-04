"""Authentication dependencies for protected API routes."""

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.auth import decode_access_token
from app.core.database import get_transaction_session
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.user_repository import UserRepository

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentMembership:
    """Authenticated membership context for the current request."""

    user: User

    @property
    def user_id(self) -> UUID:
        """Expose the authenticated user identifier."""
        return self.user.id

    @property
    def organization_id(self) -> UUID:
        """Expose the authenticated organization identifier."""
        return self.user.organization_id

    @property
    def role(self) -> UserRole:
        """Expose the user's role inside the current organization."""
        return self.user.role

    def assert_organization_access(self, organization_id: UUID) -> None:
        """Reject requests that target a different organization."""
        if self.user.organization_id != organization_id:
            raise AuthorizationError("User does not have access to this organization.")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> User:
    """Resolve the authenticated user from a bearer access token."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("Authentication credentials were not provided.")

    claims = decode_access_token(credentials.credentials)

    async with get_transaction_session() as session:
        user = await UserRepository(session).get_by_id(claims.user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Access token is invalid.")
        if user.organization is None or not user.organization.is_active:
            raise AuthenticationError("Access token is invalid.")
        if user.organization_id != claims.organization_id:
            raise AuthenticationError("Access token is invalid.")
        return user


async def get_current_membership(
    current_user: User = Depends(get_current_user),
) -> CurrentMembership:
    """Resolve the authenticated organization membership for this request."""
    return CurrentMembership(user=current_user)
