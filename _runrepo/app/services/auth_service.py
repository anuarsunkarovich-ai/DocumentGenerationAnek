"""Authentication service for internal JWT-based auth."""

from datetime import datetime, timedelta, timezone

from app.core.auth import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    verify_password,
)
from app.core.config import get_settings
from app.core.database import get_transaction_session
from app.core.exceptions import AuthenticationError, ValidationError
from app.dtos.auth import (
    AuthLoginRequest,
    AuthMembershipResponse,
    AuthOrganizationResponse,
    AuthTokenResponse,
    AuthUserResponse,
)
from app.models.auth_session import AuthSession
from app.models.user import User
from app.repositories.auth_session_repository import AuthSessionRepository
from app.repositories.user_repository import UserRepository


class AuthService:
    """Handle login, refresh, logout, and authenticated-user serialization."""

    async def login(self, payload: AuthLoginRequest) -> AuthTokenResponse:
        """Authenticate one user and issue a fresh token pair."""
        async with get_transaction_session() as session:
            user_repository = UserRepository(session)
            auth_session_repository = AuthSessionRepository(session)
            user = self._ensure_user_can_authenticate(
                await user_repository.get_by_email(payload.email)
            )
            if not verify_password(payload.password, user.password_hash):
                raise AuthenticationError("Invalid email or password.")

            await user_repository.mark_logged_in(user)
            refresh_token = generate_refresh_token()
            expires_at = datetime.now(timezone.utc) + timedelta(
                days=get_settings().auth.refresh_token_ttl_days
            )
            await auth_session_repository.create(
                AuthSession(
                    user_id=user.id,
                    refresh_token_hash=hash_refresh_token(refresh_token),
                    expires_at=expires_at,
                )
            )
            return self._build_token_response(user=user, refresh_token=refresh_token)

    async def refresh(self, refresh_token: str) -> AuthTokenResponse:
        """Rotate a valid refresh token and issue a fresh token pair."""
        async with get_transaction_session() as session:
            auth_session_repository = AuthSessionRepository(session)
            auth_session = await auth_session_repository.get_by_refresh_token_hash(
                hash_refresh_token(refresh_token)
            )
            if auth_session is None:
                raise AuthenticationError("Refresh token is invalid or expired.")
            if auth_session.revoked_at is not None or auth_session.expires_at <= datetime.now(
                timezone.utc
            ):
                raise AuthenticationError("Refresh token is invalid or expired.")

            user = self._ensure_user_can_authenticate(auth_session.user)
            await auth_session_repository.touch(auth_session)
            await auth_session_repository.revoke(auth_session)

            new_refresh_token = generate_refresh_token()
            expires_at = datetime.now(timezone.utc) + timedelta(
                days=get_settings().auth.refresh_token_ttl_days
            )
            await auth_session_repository.create(
                AuthSession(
                    user_id=user.id,
                    refresh_token_hash=hash_refresh_token(new_refresh_token),
                    expires_at=expires_at,
                )
            )
            return self._build_token_response(user=user, refresh_token=new_refresh_token)

    async def logout(self, *, refresh_token: str, current_user: User) -> None:
        """Revoke one refresh token for the authenticated user."""
        async with get_transaction_session() as session:
            auth_session_repository = AuthSessionRepository(session)
            auth_session = await auth_session_repository.get_by_refresh_token_hash(
                hash_refresh_token(refresh_token)
            )
            if auth_session is None or auth_session.user_id != current_user.id:
                return None
            if auth_session.revoked_at is None:
                await auth_session_repository.revoke(auth_session)
        return None

    def get_me(self, current_user: User) -> AuthUserResponse:
        """Serialize the authenticated user for the frontend."""
        return self._serialize_user(self._ensure_user_can_authenticate(current_user))

    def validate_password_strength(self, password: str) -> None:
        """Validate password length before user creation or reset flows."""
        if len(password) < get_settings().auth.password_min_length:
            raise ValidationError(
                f"Password must be at least {get_settings().auth.password_min_length} characters."
            )

    def _build_token_response(self, *, user: User, refresh_token: str) -> AuthTokenResponse:
        """Build one frontend-facing auth response."""
        settings = get_settings()
        access_token = create_access_token(
            user_id=user.id,
        )
        return AuthTokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            access_token_expires_in=settings.auth.access_token_ttl_seconds,
            refresh_token_expires_in=settings.auth.refresh_token_ttl_seconds,
            user=self._serialize_user(user),
        )

    def _serialize_user(self, user: User) -> AuthUserResponse:
        """Serialize one authenticated user and organization."""
        default_membership = self._get_default_membership(user)
        organization = default_membership.organization
        if organization is None:
            raise AuthenticationError("User default organization is not available.")
        return AuthUserResponse(
            id=user.id,
            organization_id=default_membership.organization_id,
            email=user.email,
            full_name=user.full_name,
            role=default_membership.role.value,
            is_active=user.is_active,
            organization=AuthOrganizationResponse(
                id=organization.id,
                name=organization.name,
                code=organization.code,
            ),
            memberships=[
                AuthMembershipResponse(
                    id=membership.id,
                    organization_id=membership.organization_id,
                    role=membership.role.value,
                    is_active=membership.is_active,
                    is_default=membership.is_default,
                    organization=AuthOrganizationResponse(
                        id=membership.organization.id,
                        name=membership.organization.name,
                        code=membership.organization.code,
                    ),
                )
                for membership in self._get_active_memberships(user)
            ],
        )

    def _ensure_user_can_authenticate(self, user: User | None) -> User:
        """Ensure the user and organization are active before issuing tokens."""
        if user is None or not user.is_active:
            raise AuthenticationError("Invalid email or password.")
        if not self._get_active_memberships(user):
            raise AuthenticationError("User does not have an active organization membership.")
        return user

    def _get_active_memberships(self, user: User) -> list:
        """Return memberships that remain active and point to active organizations."""
        return [
            membership
            for membership in user.memberships
            if membership.is_active
            and membership.organization is not None
            and membership.organization.is_active
        ]

    def _get_default_membership(self, user: User):
        """Return the default membership for the authenticated user."""
        memberships = self._get_active_memberships(user)
        default_membership = next((item for item in memberships if item.is_default), None)
        if default_membership is not None:
            return default_membership
        if len(memberships) == 1:
            return memberships[0]
        raise AuthenticationError("User does not have a default organization membership.")
