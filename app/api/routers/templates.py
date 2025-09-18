"""Template management API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from app.api.controllers.template_controller import TemplateController
from app.dtos.template import (
    TemplateAccessQuery,
    TemplateDetailResponse,
    TemplateIngestionResponse,
    TemplateListQuery,
    TemplateListResponse,
    TemplateRegisterRequest,
    TemplateSchemaExtractionResponse,
    TemplateSchemaResponse,
    TemplateUploadRequest,
)
from app.services.template_service import TemplateService

router = APIRouter()


def build_template_upload_request(
    organization_id: Annotated[UUID, Form(...)],
    name: Annotated[str, Form(...)],
    code: Annotated[str, Form(...)],
    version: Annotated[str, Form(...)],
    description: Annotated[str | None, Form()] = None,
    notes: Annotated[str | None, Form()] = None,
    created_by_user_id: Annotated[UUID | None, Form()] = None,
    publish: Annotated[bool, Form()] = True,
) -> TemplateUploadRequest:
    """Build a validated DTO from multipart form fields."""
    return TemplateUploadRequest(
        organization_id=organization_id,
        name=name,
        code=code,
        version=version,
        description=description,
        notes=notes,
        created_by_user_id=created_by_user_id,
        publish=publish,
    )


@router.get("", response_model=TemplateListResponse)
async def list_templates(
    query: Annotated[TemplateListQuery, Depends()],
) -> TemplateListResponse:
    """Return all templates visible to the selected tenant."""
    controller = TemplateController(service=TemplateService())
    return await controller.list_templates(organization_id=query.organization_id)


@router.post(
    "/upload",
    response_model=TemplateIngestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_template(
    payload: Annotated[TemplateUploadRequest, Depends(build_template_upload_request)],
    file: UploadFile = File(...),
) -> TemplateIngestionResponse:
    """Upload a DOCX template, extract its schema, and persist it."""
    controller = TemplateController(service=TemplateService())
    return await controller.upload_template(
        organization_id=payload.organization_id,
        name=payload.name,
        code=payload.code,
        version=payload.version,
        file=file,
        description=payload.description,
        notes=payload.notes,
        created_by_user_id=payload.created_by_user_id,
        publish=payload.publish,
    )


@router.post(
    "/register",
    response_model=TemplateIngestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_template(payload: TemplateRegisterRequest) -> TemplateIngestionResponse:
    """Register a DOCX template that already exists in storage."""
    controller = TemplateController(service=TemplateService())
    return await controller.register_template(payload)


@router.post(
    "/extract-schema",
    response_model=TemplateSchemaResponse,
    status_code=status.HTTP_200_OK,
)
async def extract_template_schema(file: UploadFile = File(...)) -> TemplateSchemaResponse:
    """Extract a normalized frontend schema without persisting a template."""
    controller = TemplateController(service=TemplateService())
    return await controller.extract_schema_from_upload(file)


@router.get("/{template_id}", response_model=TemplateDetailResponse)
async def get_template(
    template_id: UUID,
    query: Annotated[TemplateAccessQuery, Depends()],
) -> TemplateDetailResponse:
    """Return one template with its current version details."""
    controller = TemplateController(service=TemplateService())
    return await controller.get_template(
        organization_id=query.organization_id,
        template_id=template_id,
    )


@router.post(
    "/{template_id}/extract-schema",
    response_model=TemplateSchemaExtractionResponse,
    status_code=status.HTTP_200_OK,
)
async def extract_stored_template_schema(
    template_id: UUID,
    query: Annotated[TemplateAccessQuery, Depends()],
) -> TemplateSchemaExtractionResponse:
    """Re-extract schema from the current stored template version."""
    controller = TemplateController(service=TemplateService())
    return await controller.extract_schema_for_template(
        organization_id=query.organization_id,
        template_id=template_id,
    )
