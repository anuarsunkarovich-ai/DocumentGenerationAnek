"""Authentication dependencies for protected API routes."""

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.auth import decode_access_token
from app.core.database import get_transaction_session
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.request_context import bind_request_state
from app.models.enums import UserRole
from app.models.organization_membership import OrganizationMembership
from app.models.user import User
from app.repositories.user_repository import UserRepository

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentMembership:
    """Authenticated membership context for the current request."""

    user: User
    membership: OrganizationMembership

    @property
    def user_id(self) -> UUID:
        """Expose the authenticated user identifier."""
        return self.user.id

    @property
    def organization_id(self) -> UUID:
        """Expose the authenticated organization identifier."""
        return self.membership.organization_id

    @property
    def role(self) -> UserRole:
        """Expose the user's role inside the current organization."""
        return self.membership.role

    def assert_organization_access(self, organization_id: UUID) -> None:
        """Reject requests that target a different organization."""
        if self.membership.organization_id != organization_id:
            raise AuthorizationError("User does not have access to this organization.")


def resolve_membership(
    *,
    user: User,
    organization_id: UUID | None = None,
) -> CurrentMembership:
    """Resolve one active membership for the authenticated user."""
    memberships = [
        membership
        for membership in user.memberships
        if membership.is_active
        and membership.organization is not None
        and membership.organization.is_active
    ]
    if not memberships:
        raise AuthorizationError("User does not have an active organization membership.")

    if organization_id is not None:
        membership = next(
            (item for item in memberships if item.organization_id == organization_id),
            None,
        )
        if membership is None:
            raise AuthorizationError("User does not have access to this organization.")
        return CurrentMembership(user=user, membership=membership)

    default_membership = next((item for item in memberships if item.is_default), None)
    if default_membership is not None:
        return CurrentMembership(user=user, membership=default_membership)
    if len(memberships) == 1:
        return CurrentMembership(user=user, membership=memberships[0])
    raise AuthorizationError("Organization selection is required for this user.")


async def get_current_user(
    request: Request,
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
        if not any(
            membership.is_active
            and membership.organization is not None
            and membership.organization.is_active
            for membership in user.memberships
        ):
            raise AuthenticationError("Access token is invalid.")
        bind_request_state(request, user_id=user.id)
        return user


async def get_current_membership(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> CurrentMembership:
    """Resolve the authenticated organization membership for this request."""
    membership = resolve_membership(user=current_user)
    bind_request_state(
        request,
        user_id=membership.user_id,
        organization_id=membership.organization_id,
    )
    return membership
