"""Repository for organization persistence."""

from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization


class OrganizationRepository:
    """Access organization records."""

    def __init__(self, session: AsyncSession) -> None:
        """Store the active database session."""
        self._session = session

    async def get_by_id(self, organization_id: UUID) -> Organization | None:
        """Return an organization by its identifier."""
        statement: Select[tuple[Organization]] = select(Organization).where(
            Organization.id == organization_id
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()
