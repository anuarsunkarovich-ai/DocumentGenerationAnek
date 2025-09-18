"""Repository for template version persistence."""

from uuid import UUID

from sqlalchemy import Select, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.template_version import TemplateVersion


class TemplateVersionRepository:
    """Access template version records."""

    def __init__(self, session: AsyncSession) -> None:
        """Store the active database session."""
        self._session = session

    async def create(self, template_version: TemplateVersion) -> TemplateVersion:
        """Persist a template version and refresh it."""
        self._session.add(template_version)
        await self._session.flush()
        await self._session.refresh(template_version)
        return template_version

    async def update_schema(
        self,
        template_version: TemplateVersion,
        *,
        variable_schema: dict,
        component_schema: list[dict],
    ) -> TemplateVersion:
        """Persist refreshed schema data for an existing template version."""
        template_version.variable_schema = variable_schema
        template_version.component_schema = component_schema
        await self._session.flush()
        await self._session.refresh(template_version)
        return template_version

    async def get_by_template_and_version(
        self,
        *,
        template_id: UUID,
        version: str,
    ) -> TemplateVersion | None:
        """Return a template version by its semantic version string."""
        statement: Select[tuple[TemplateVersion]] = select(TemplateVersion).where(
            TemplateVersion.template_id == template_id,
            TemplateVersion.version == version,
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def unset_current_versions(self, template_id: UUID) -> None:
        """Clear the current flag for all versions of a template."""
        statement = (
            update(TemplateVersion)
            .where(TemplateVersion.template_id == template_id)
            .values(is_current=False)
        )
        await self._session.execute(statement)

    async def get_by_id(self, template_version_id: UUID) -> TemplateVersion | None:
        """Return a template version by identifier."""
        statement: Select[tuple[TemplateVersion]] = select(TemplateVersion).where(
            TemplateVersion.id == template_version_id
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_current_for_template(self, template_id: UUID) -> TemplateVersion | None:
        """Return the current template version for a template."""
        statement: Select[tuple[TemplateVersion]] = select(TemplateVersion).where(
            TemplateVersion.template_id == template_id,
            TemplateVersion.is_current.is_(True),
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()
