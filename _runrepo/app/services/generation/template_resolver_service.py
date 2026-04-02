"""Resolve templates and versions for generation jobs."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.template import Template
from app.models.template_version import TemplateVersion
from app.repositories.template_repository import TemplateRepository
from app.repositories.template_version_repository import TemplateVersionRepository
from app.services.generation.models import ResolvedTemplateContext


class TemplateResolverService:
    """Resolve template and template-version data for generation."""

    def __init__(self, session: AsyncSession) -> None:
        """Store the active database session."""
        self._template_repository = TemplateRepository(session)
        self._template_version_repository = TemplateVersionRepository(session)

    async def resolve(
        self,
        *,
        organization_id: UUID,
        template_id: UUID,
        template_version_id: UUID | None,
        require_published: bool = False,
    ) -> ResolvedTemplateContext:
        """Resolve the requested template and generation version."""
        template = await self._template_repository.get_by_id(
            template_id=template_id,
            organization_id=organization_id,
            published_only=require_published,
        )
        if template is None:
            raise NotFoundError("Template was not found.")

        if template_version_id is None:
            template_version = await self._template_version_repository.get_current_for_template(
                template.id
            )
        else:
            template_version = await self._template_version_repository.get_by_id(
                template_version_id
            )

        if template_version is None or template_version.template_id != template.id:
            raise NotFoundError("Template version was not found.")
        if require_published and not template_version.is_published:
            raise NotFoundError("Template version was not found.")

        return self._to_context(template=template, template_version=template_version)

    def _to_context(
        self,
        *,
        template: Template,
        template_version: TemplateVersion,
    ) -> ResolvedTemplateContext:
        """Convert ORM entities into the generation context model."""
        if template.organization is None:
            raise NotFoundError("Template organization was not found.")

        return ResolvedTemplateContext(
            template_id=template.id,
            template_version_id=template_version.id,
            organization_id=template.organization_id,
            organization_code=template.organization.code,
            template_code=template.code,
            template_name=template.name,
            template_version=template_version.version,
            original_filename=template_version.original_filename,
            variable_schema=template_version.variable_schema,
            storage_key=template_version.storage_key,
            render_strategy=template_version.render_strategy,
            import_bindings=template_version.import_bindings,
        )
