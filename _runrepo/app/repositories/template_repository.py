"""Repository for template persistence."""

from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.template import Template


class TemplateRepository:
    """Access template records."""

    def __init__(self, session: AsyncSession) -> None:
        """Store the active database session."""
        self._session = session

    async def list_all(self, organization_id: UUID, *, published_only: bool = False) -> list[Template]:
        """Return templates for one organization."""
        statement: Select[tuple[Template]] = (
            select(Template)
            .options(selectinload(Template.versions))
            .order_by(Template.created_at.desc())
            .where(Template.organization_id == organization_id)
        )
        if published_only:
            from app.models.template_version import TemplateVersion

            statement = statement.join(TemplateVersion).where(
                TemplateVersion.is_current.is_(True),
                TemplateVersion.is_published.is_(True),
            )

        result = await self._session.execute(statement)
        return list(result.scalars().unique().all())

    async def get_by_code(
        self,
        *,
        organization_id: UUID,
        code: str,
    ) -> Template | None:
        """Return a template by tenant and business code."""
        statement: Select[tuple[Template]] = (
            select(Template)
            .options(selectinload(Template.versions))
            .where(
                Template.organization_id == organization_id,
                Template.code == code,
            )
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_id(
        self,
        *,
        template_id: UUID,
        organization_id: UUID,
        published_only: bool = False,
    ) -> Template | None:
        """Return a template by identifier within one organization."""
        statement: Select[tuple[Template]] = (
            select(Template)
            .options(selectinload(Template.versions), selectinload(Template.organization))
            .where(
                Template.id == template_id,
                Template.organization_id == organization_id,
            )
        )
        if published_only:
            from app.models.template_version import TemplateVersion

            statement = statement.join(TemplateVersion).where(
                TemplateVersion.is_current.is_(True),
                TemplateVersion.is_published.is_(True),
            )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def create(self, template: Template) -> Template:
        """Persist a template and refresh it."""
        self._session.add(template)
        await self._session.flush()
        await self._session.refresh(template)
        return template

    async def count_by_organization(self, organization_id: UUID) -> int:
        """Return the number of logical templates for one organization."""
        statement = select(func.count(Template.id)).where(Template.organization_id == organization_id)
        result = await self._session.execute(statement)
        return int(result.scalar_one())
