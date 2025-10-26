"""Document generation API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status

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
    task_id: UUID,
    query: Annotated[DocumentJobAccessQuery, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DocumentJobStatusResponse:
    """Return the current status and artifacts for a generation job."""
    require_job_read_access(current_user, query.organization_id)
    controller = DocumentController(service=DocumentService())
    return await controller.get_job_status(
        organization_id=query.organization_id,
        job_id=task_id,
    )


@router.get("/jobs/{task_id}/download", response_model=DocumentArtifactAccessResponse)
async def get_document_job_download(
    task_id: UUID,
    query: Annotated[DocumentJobAccessQuery, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DocumentArtifactAccessResponse:
    """Return the best downloadable artifact for a generation job."""
    require_job_read_access(current_user, query.organization_id)
    controller = DocumentController(service=DocumentService())
    return await controller.get_download_artifact(
        organization_id=query.organization_id,
        job_id=task_id,
    )


@router.get("/jobs/{task_id}/preview", response_model=DocumentArtifactAccessResponse)
async def get_document_job_preview(
    task_id: UUID,
    query: Annotated[DocumentJobAccessQuery, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DocumentArtifactAccessResponse:
    """Return the best preview artifact for a generation job."""
    require_job_read_access(current_user, query.organization_id)
    controller = DocumentController(service=DocumentService())
    return await controller.get_preview_artifact(
        organization_id=query.organization_id,
        job_id=task_id,
    )


@router.post("/jobs", response_model=DocumentJobResponse, status_code=status.HTTP_202_ACCEPTED)
@router.post("/generate", response_model=DocumentJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_document_job(
    payload: DocumentJobCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
) -> DocumentJobResponse:
    """Queue a new document generation job."""
    membership = require_generation_access(current_user, payload.organization_id)
    controller = DocumentController(service=DocumentService())
    return await controller.create_job(
        payload,
        background_tasks,
        current_user_id=membership.user_id,
    )
