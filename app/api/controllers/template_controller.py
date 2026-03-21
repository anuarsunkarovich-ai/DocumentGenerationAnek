"""Controller helpers for template endpoints."""

from uuid import UUID

from fastapi import UploadFile

from app.dtos.template import (
    TemplateDetailResponse,
    TemplateImportAnalysisResponse,
    TemplateImportConfirmationResponse,
    TemplateImportConfirmRequest,
    TemplateImportInspectionResponse,
    TemplateImportTemplateizeRequest,
    TemplateIngestionResponse,
    TemplateListResponse,
    TemplateRegisterRequest,
    TemplateSchemaExtractionResponse,
    TemplateSchemaResponse,
    TemplateTemplateizationConfirmationResponse,
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

    async def analyze_import_from_upload(self, file: UploadFile) -> TemplateImportAnalysisResponse:
        """Analyze a regular DOCX upload before import confirmation."""
        return await self._service.analyze_import_from_upload(file)

    async def inspect_import_from_upload(self, file: UploadFile) -> TemplateImportInspectionResponse:
        """Inspect a DOCX upload for assisted templateization."""
        return await self._service.inspect_import_from_upload(file)

    async def analyze_import_for_template(
        self,
        *,
        organization_id: UUID,
        template_id: UUID,
    ) -> TemplateImportAnalysisResponse:
        """Analyze the current stored DOCX template as an imported document."""
        return await self._service.analyze_import_for_template(
            organization_id=organization_id,
            template_id=template_id,
        )

    async def inspect_import_for_template(
        self,
        *,
        organization_id: UUID,
        template_id: UUID,
    ) -> TemplateImportInspectionResponse:
        """Inspect the current stored DOCX template for assisted templateization."""
        return await self._service.inspect_import_for_template(
            organization_id=organization_id,
            template_id=template_id,
        )

    async def confirm_import_for_template(
        self,
        *,
        organization_id: UUID,
        template_id: UUID,
        payload: TemplateImportConfirmRequest,
    ) -> TemplateImportConfirmationResponse:
        """Persist confirmed imported-DOCX bindings for a stored template."""
        return await self._service.confirm_import_for_template(
            organization_id=organization_id,
            template_id=template_id,
            payload=payload,
        )

    async def templateize_import_for_template(
        self,
        *,
        organization_id: UUID,
        template_id: UUID,
        payload: TemplateImportTemplateizeRequest,
    ) -> TemplateTemplateizationConfirmationResponse:
        """Persist manual selections for assisted DOCX templateization."""
        return await self._service.templateize_import_for_template(
            organization_id=organization_id,
            template_id=template_id,
            payload=payload,
        )
