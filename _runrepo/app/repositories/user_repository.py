"""Repository for user persistence."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Select, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.organization_membership import OrganizationMembership
from app.models.user import User


class UserRepository:
    """Access user records for authentication and ownership lookups."""

    def __init__(self, session: AsyncSession) -> None:
        """Store the active database session."""
        self._session = session

    async def get_by_email(self, email: str) -> User | None:
        """Return one user by normalized email address."""
        statement: Select[tuple[User]] = (
            select(User)
            .options(
                selectinload(User.organization),
                selectinload(User.memberships).selectinload(OrganizationMembership.organization),
            )
            .where(User.email == email.lower().strip())
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Return one user by identifier with organization loaded."""
        statement: Select[tuple[User]] = (
            select(User)
            .options(
                selectinload(User.organization),
                selectinload(User.memberships).selectinload(OrganizationMembership.organization),
            )
            .where(User.id == user_id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def mark_logged_in(self, user: User) -> User:
        """Persist the last successful login timestamp."""
        user.last_login_at = datetime.now(timezone.utc)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def count_active_for_organization(self, organization_id: UUID) -> int:
        """Return active user seats for one organization based on memberships."""
        statement = (
            select(func.count(distinct(OrganizationMembership.user_id)))
            .select_from(OrganizationMembership)
            .join(User, User.id == OrganizationMembership.user_id)
            .where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.is_active.is_(True),
                User.is_active.is_(True),
            )
        )
        result = await self._session.execute(statement)
        return int(result.scalar_one())

    async def set_active(self, user: User, *, is_active: bool) -> User:
        """Enable or disable one user account."""
        user.is_active = is_active
        await self._session.flush()
        await self._session.refresh(user)
        return user
