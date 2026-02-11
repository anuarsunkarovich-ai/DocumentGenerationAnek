"""Public machine-auth routes for document generation and polling."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status

from app.api.controllers.document_controller import DocumentController
from app.api.dependencies.api_keys import require_api_key_scope
from app.dtos.api_key import ApiKeyScope
from app.dtos.document import (
    ConstructorSchemaResponse,
    DocumentArtifactAccessResponse,
    DocumentJobCreateRequest,
    DocumentJobResponse,
    DocumentJobStatusResponse,
    PublicDocumentJobCreateRequest,
)
from app.services.api_key_service import ApiKeyPrincipal
from app.services.document_service import DocumentService

router = APIRouter(prefix="/public/documents", tags=["public-documents"])


@router.get("/constructor-schema", response_model=ConstructorSchemaResponse)
async def get_public_constructor_schema(
    principal: Annotated[
        ApiKeyPrincipal,
        Depends(require_api_key_scope(ApiKeyScope.DOCUMENTS_GENERATE)),
    ],
) -> ConstructorSchemaResponse:
    """Return the constructor schema for machine clients."""
    _ = principal
    controller = DocumentController(service=DocumentService())
    return await controller.get_constructor_schema()


@router.post("/generate", response_model=DocumentJobResponse, status_code=status.HTTP_202_ACCEPTED)
@router.post("/jobs", response_model=DocumentJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_public_document_job(
    payload: PublicDocumentJobCreateRequest,
    background_tasks: BackgroundTasks,
    principal: Annotated[
        ApiKeyPrincipal,
        Depends(require_api_key_scope(ApiKeyScope.DOCUMENTS_GENERATE)),
    ],
) -> DocumentJobResponse:
    """Queue a public document generation job inside the API key's organization."""
    controller = DocumentController(service=DocumentService())
    internal_payload = DocumentJobCreateRequest(
        organization_id=principal.organization_id,
        template_id=payload.template_id,
        template_version_id=payload.template_version_id,
        data=payload.data,
        constructor=payload.constructor,
    )
    return await controller.create_job(
        internal_payload,
        background_tasks,
        current_user_id=None,
        current_api_key_id=principal.api_key_id,
        require_published_template=True,
    )


@router.get("/jobs/{task_id}", response_model=DocumentJobStatusResponse)
async def get_public_document_job_status(
    task_id: UUID,
    principal: Annotated[
        ApiKeyPrincipal,
        Depends(require_api_key_scope(ApiKeyScope.DOCUMENTS_READ)),
    ],
) -> DocumentJobStatusResponse:
    """Return the current status of a public document job."""
    controller = DocumentController(service=DocumentService())
    return await controller.get_job_status(
        organization_id=principal.organization_id,
        job_id=task_id,
    )


@router.get("/jobs/{task_id}/download", response_model=DocumentArtifactAccessResponse)
async def get_public_document_download(
    task_id: UUID,
    principal: Annotated[
        ApiKeyPrincipal,
        Depends(require_api_key_scope(ApiKeyScope.DOCUMENTS_READ)),
    ],
) -> DocumentArtifactAccessResponse:
    """Return the preferred downloadable artifact for a public job."""
    controller = DocumentController(service=DocumentService())
    return await controller.get_download_artifact(
        organization_id=principal.organization_id,
        job_id=task_id,
    )


@router.get("/jobs/{task_id}/preview", response_model=DocumentArtifactAccessResponse)
async def get_public_document_preview(
    task_id: UUID,
    principal: Annotated[
        ApiKeyPrincipal,
        Depends(require_api_key_scope(ApiKeyScope.DOCUMENTS_READ)),
    ],
) -> DocumentArtifactAccessResponse:
    """Return the preferred preview artifact for a public job."""
    controller = DocumentController(service=DocumentService())
    return await controller.get_preview_artifact(
        organization_id=principal.organization_id,
        job_id=task_id,
    )
