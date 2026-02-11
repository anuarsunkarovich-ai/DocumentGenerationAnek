"""Controller helpers for template endpoints."""

from uuid import UUID

from fastapi import UploadFile

from app.dtos.template import (
    TemplateDetailResponse,
    TemplateIngestionResponse,
    TemplateListResponse,
    TemplateRegisterRequest,
    TemplateSchemaExtractionResponse,
    TemplateSchemaResponse,
)
from app.services.template_service import TemplateService


class TemplateController:
    """Coordinate template-related requests."""

    def __init__(self, service: TemplateService) -> None:
        self._service = service

    async def list_templates(
        self,
        organization_id: UUID,
        *,
        published_only: bool = False,
    ) -> TemplateListResponse:
        """Return the currently registered templates."""
        return await self._service.list_templates(
            organization_id=organization_id,
            published_only=published_only,
        )

    async def get_template(
        self,
        *,
        organization_id: UUID,
        template_id: UUID,
        published_only: bool = False,
    ) -> TemplateDetailResponse:
        """Return one template with version details."""
        return await self._service.get_template(
            organization_id=organization_id,
            template_id=template_id,
            published_only=published_only,
        )

    async def extract_schema_for_template(
        self,
        *,
        organization_id: UUID,
        template_id: UUID,
    ) -> TemplateSchemaExtractionResponse:
        """Re-extract schema for a stored template."""
        return await self._service.extract_schema_for_template(
            organization_id=organization_id,
            template_id=template_id,
        )

    async def upload_template(
        self,
        *,
        organization_id: UUID,
        name: str,
        code: str,
        version: str,
        file: UploadFile,
        description: str | None = None,
        notes: str | None = None,
        current_user_id: UUID,
        publish: bool = True,
    ) -> TemplateIngestionResponse:
        """Upload and register a DOCX template."""
        return await self._service.upload_template(
            organization_id=organization_id,
            name=name,
            code=code,
            version=version,
            file=file,
            description=description,
            notes=notes,
            current_user_id=current_user_id,
            publish=publish,
        )

    async def register_template(
        self,
        payload: TemplateRegisterRequest,
        *,
        current_user_id: UUID,
    ) -> TemplateIngestionResponse:
        """Register a DOCX template from existing storage."""
        return await self._service.register_template(payload, current_user_id=current_user_id)

    async def extract_schema_from_upload(self, file: UploadFile) -> TemplateSchemaResponse:
        """Extract a normalized schema from a DOCX upload."""
        return await self._service.extract_schema_from_upload(file)
