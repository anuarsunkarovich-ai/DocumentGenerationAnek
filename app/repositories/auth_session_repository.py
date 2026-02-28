"""Repository for refresh-session persistence."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.auth_session import AuthSession
from app.models.organization_membership import OrganizationMembership
from app.models.user import User


class AuthSessionRepository:
    """Access revocable refresh sessions."""

    def __init__(self, session: AsyncSession) -> None:
        """Store the active database session."""
        self._session = session

    async def create(self, auth_session: AuthSession) -> AuthSession:
        """Persist a refresh session."""
        self._session.add(auth_session)
        await self._session.flush()
        await self._session.refresh(auth_session)
        return auth_session

    async def get_by_refresh_token_hash(self, refresh_token_hash: str) -> AuthSession | None:
        """Return one refresh session by its hashed token value."""
        statement: Select[tuple[AuthSession]] = (
            select(AuthSession)
            .options(
                selectinload(AuthSession.user).selectinload(User.organization),
                selectinload(AuthSession.user)
                .selectinload(User.memberships)
                .selectinload(OrganizationMembership.organization),
            )
            .where(AuthSession.refresh_token_hash == refresh_token_hash)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def revoke(self, auth_session: AuthSession) -> AuthSession:
        """Revoke a refresh session."""
        auth_session.revoked_at = datetime.now(timezone.utc)
        await self._session.flush()
        await self._session.refresh(auth_session)
        return auth_session

    async def touch(self, auth_session: AuthSession) -> AuthSession:
        """Update the last-used timestamp for a refresh session."""
        auth_session.last_used_at = datetime.now(timezone.utc)
        await self._session.flush()
        await self._session.refresh(auth_session)
        return auth_session

    async def revoke_all_for_user(self, *, user_id: UUID) -> int:
        """Revoke every active refresh session for one user."""
        statement: Select[tuple[AuthSession]] = (
            select(AuthSession).where(
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
            )
        )
        result = await self._session.execute(statement)
        sessions = list(result.scalars().all())
        revoked_at = datetime.now(timezone.utc)
        for auth_session in sessions:
            auth_session.revoked_at = revoked_at
        if sessions:
            await self._session.flush()
        return len(sessions)
