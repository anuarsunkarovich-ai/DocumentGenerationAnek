"""Document generation API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile, status

from app.api.controllers.document_controller import DocumentController
from app.api.dependencies.auth import (
    CurrentMembership,
    get_current_membership,
    get_current_user,
)
from app.api.dependencies.authorization import (
    require_generation_access,
    require_job_read_access,
)
from app.dtos.document import (
    ConstructorSchemaResponse,
    DocumentArtifactAccessResponse,
    DocumentJobAccessQuery,
    DocumentJobCreateRequest,
    DocumentJobResponse,
    DocumentJobStatusResponse,
    DocumentVerificationResponse,
    ImportedTemplateDocumentJobCreateRequest,
)
from app.models.user import User
from app.services.document_service import DocumentService

router = APIRouter()


@router.get("/constructor-schema", response_model=ConstructorSchemaResponse)
async def get_constructor_schema(
    membership: Annotated[CurrentMembership, Depends(get_current_membership)],
) -> ConstructorSchemaResponse:
    """Return the supported component-driven constructor schema."""
    _ = membership
    controller = DocumentController(service=DocumentService())
    return await controller.get_constructor_schema()


@router.get("/jobs/{task_id}", response_model=DocumentJobStatusResponse)
async def get_document_job_status(
    request: Request,
    task_id: UUID,
    query: Annotated[DocumentJobAccessQuery, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DocumentJobStatusResponse:
    """Return the current status and artifacts for a generation job."""
    require_job_read_access(current_user, query.organization_id, request=request)
    controller = DocumentController(service=DocumentService())
    return await controller.get_job_status(
        organization_id=query.organization_id,
        job_id=task_id,
    )


@router.get("/jobs/{task_id}/download", response_model=DocumentArtifactAccessResponse)
async def get_document_job_download(
    request: Request,
    task_id: UUID,
    query: Annotated[DocumentJobAccessQuery, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DocumentArtifactAccessResponse:
    """Return the best downloadable artifact for a generation job."""
    require_job_read_access(current_user, query.organization_id, request=request)
    controller = DocumentController(service=DocumentService())
    return await controller.get_download_artifact(
        organization_id=query.organization_id,
        job_id=task_id,
    )


@router.get("/jobs/{task_id}/preview", response_model=DocumentArtifactAccessResponse)
async def get_document_job_preview(
    request: Request,
    task_id: UUID,
    query: Annotated[DocumentJobAccessQuery, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DocumentArtifactAccessResponse:
    """Return the best preview artifact for a generation job."""
    require_job_read_access(current_user, query.organization_id, request=request)
    controller = DocumentController(service=DocumentService())
    return await controller.get_preview_artifact(
        organization_id=query.organization_id,
        job_id=task_id,
    )


@router.post("/verify", response_model=DocumentVerificationResponse)
async def verify_document_artifact(
    request: Request,
    organization_id: Annotated[UUID, Form(...)],
    current_user: Annotated[User, Depends(get_current_user)],
    authenticity_hash: Annotated[str | None, Form()] = None,
    file: UploadFile | None = File(default=None),
) -> DocumentVerificationResponse:
    """Return whether a file or hash matches one generated artifact in this organization."""
    require_job_read_access(current_user, organization_id, request=request)
    file_bytes = await file.read() if file is not None else None
    controller = DocumentController(service=DocumentService())
    return await controller.verify_artifact(
        organization_id=organization_id,
        authenticity_hash=authenticity_hash,
        file_bytes=file_bytes,
    )


@router.post("/jobs", response_model=DocumentJobResponse, status_code=status.HTTP_202_ACCEPTED)
@router.post("/generate", response_model=DocumentJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_document_job(
    request: Request,
    payload: DocumentJobCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
) -> DocumentJobResponse:
    """Queue a new document generation job."""
    membership = require_generation_access(current_user, payload.organization_id, request=request)
    controller = DocumentController(service=DocumentService())
    return await controller.create_job(
        payload,
        background_tasks,
        current_user_id=membership.user_id,
    )


@router.post(
    "/generate-imported",
    response_model=DocumentJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_imported_document_job(
    request: Request,
    payload: ImportedTemplateDocumentJobCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
) -> DocumentJobResponse:
    """Queue a DOCX-preserving generation job for an imported template."""
    membership = require_generation_access(current_user, payload.organization_id, request=request)
    controller = DocumentController(service=DocumentService())
    return await controller.create_imported_job(
        payload,
        background_tasks,
        current_user_id=membership.user_id,
    )
