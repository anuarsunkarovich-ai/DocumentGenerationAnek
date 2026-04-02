"""Controller helpers for document generation endpoints."""

from uuid import UUID

from fastapi import BackgroundTasks

from app.dtos.document import (
    ConstructorSchemaResponse,
    DocumentArtifactAccessResponse,
    DocumentJobCreateRequest,
    DocumentJobResponse,
    DocumentJobStatusResponse,
    DocumentVerificationResponse,
    ImportedTemplateDocumentJobCreateRequest,
)
from app.services.document_service import DocumentService


class DocumentController:
    """Coordinate document generation requests."""

    def __init__(self, service: DocumentService) -> None:
        self._service = service

    async def create_job(
        self,
        payload: DocumentJobCreateRequest,
        background_tasks: BackgroundTasks,
        *,
        current_user_id: UUID | None,
        current_api_key_id: UUID | None = None,
        require_published_template: bool = False,
    ) -> DocumentJobResponse:
        """Create a document generation job."""
        return await self._service.create_job(
            payload,
            background_tasks,
            current_user_id=current_user_id,
            current_api_key_id=current_api_key_id,
            require_published_template=require_published_template,
        )

    async def create_imported_job(
        self,
        payload: ImportedTemplateDocumentJobCreateRequest,
        background_tasks: BackgroundTasks,
        *,
        current_user_id: UUID | None,
        current_api_key_id: UUID | None = None,
        require_published_template: bool = False,
    ) -> DocumentJobResponse:
        """Create a document generation job for a confirmed imported DOCX template."""
        return await self._service.create_imported_job(
            payload,
            background_tasks,
            current_user_id=current_user_id,
            current_api_key_id=current_api_key_id,
            require_published_template=require_published_template,
        )

    async def get_job_status(
        self,
        *,
        organization_id: UUID,
        job_id: UUID,
    ) -> DocumentJobStatusResponse:
        """Return the current generation status for a tenant-scoped job."""
        return await self._service.get_job_status(
            organization_id=organization_id,
            job_id=job_id,
        )

    async def get_download_artifact(
        self,
        *,
        organization_id: UUID,
        job_id: UUID,
    ) -> DocumentArtifactAccessResponse:
        """Return the best available downloadable artifact."""
        return await self._service.get_download_artifact(
            organization_id=organization_id,
            job_id=job_id,
        )

    async def get_preview_artifact(
        self,
        *,
        organization_id: UUID,
        job_id: UUID,
    ) -> DocumentArtifactAccessResponse:
        """Return the best available preview artifact."""
        return await self._service.get_preview_artifact(
            organization_id=organization_id,
            job_id=job_id,
        )

    async def get_constructor_schema(self) -> ConstructorSchemaResponse:
        """Return the supported constructor contract."""
        return await self._service.get_constructor_schema()

    async def verify_artifact(
        self,
        *,
        organization_id: UUID,
        authenticity_hash: str | None = None,
        file_bytes: bytes | None = None,
    ) -> DocumentVerificationResponse:
        """Return whether an uploaded file or hash matches a stored artifact."""
        return await self._service.verify_artifact(
            organization_id=organization_id,
            authenticity_hash=authenticity_hash,
            file_bytes=file_bytes,
        )
