"""Template management API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status

from app.api.controllers.template_controller import TemplateController
from app.api.dependencies.auth import get_current_user
from app.api.dependencies.authorization import (
    require_template_read_access,
    require_template_write_access,
)
from app.dtos.template import (
    TemplateAccessQuery,
    TemplateDetailResponse,
    TemplateImportAnalysisResponse,
    TemplateImportAnalyzeStoredRequest,
    TemplateImportConfirmationResponse,
    TemplateImportConfirmRequest,
    TemplateImportInspectionResponse,
    TemplateImportTemplateizeRequest,
    TemplateIngestionResponse,
    TemplateListQuery,
    TemplateListResponse,
    TemplateRegisterRequest,
    TemplateSchemaExtractionResponse,
    TemplateSchemaResponse,
    TemplateTemplateizationConfirmationResponse,
    TemplateUploadRequest,
)
from app.models.user import User
from app.services.template_service import TemplateService

router = APIRouter()


def build_template_upload_request(
    organization_id: Annotated[UUID, Form(...)],
    name: Annotated[str, Form(...)],
    code: Annotated[str, Form(...)],
    version: Annotated[str, Form(...)],
    description: Annotated[str | None, Form()] = None,
    notes: Annotated[str | None, Form()] = None,
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
        publish=publish,
    )


@router.get("", response_model=TemplateListResponse)
async def list_templates(
    request: Request,
    query: Annotated[TemplateListQuery, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TemplateListResponse:
    """Return all templates visible to the selected tenant."""
    require_template_read_access(current_user, query.organization_id, request=request)
    controller = TemplateController(service=TemplateService())
    return await controller.list_templates(organization_id=query.organization_id)


@router.post(
    "/upload",
    response_model=TemplateIngestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_template(
    request: Request,
    payload: Annotated[TemplateUploadRequest, Depends(build_template_upload_request)],
    current_user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
) -> TemplateIngestionResponse:
    """Upload a DOCX template, extract its schema, and persist it."""
    membership = require_template_write_access(current_user, payload.organization_id, request=request)
    controller = TemplateController(service=TemplateService())
    return await controller.upload_template(
        organization_id=payload.organization_id,
        name=payload.name,
        code=payload.code,
        version=payload.version,
        file=file,
        description=payload.description,
        notes=payload.notes,
        current_user_id=membership.user_id,
        publish=payload.publish,
    )


@router.post(
    "/register",
    response_model=TemplateIngestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_template(
    request: Request,
    payload: TemplateRegisterRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> TemplateIngestionResponse:
    """Register a DOCX template that already exists in storage."""
    membership = require_template_write_access(current_user, payload.organization_id, request=request)
    controller = TemplateController(service=TemplateService())
    return await controller.register_template(
        payload,
        current_user_id=membership.user_id,
    )


@router.post(
    "/extract-schema",
    response_model=TemplateSchemaResponse,
    status_code=status.HTTP_200_OK,
)
async def extract_template_schema(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
) -> TemplateSchemaResponse:
    """Extract a normalized frontend schema without persisting a template."""
    membership = require_template_write_access(current_user, request=request)
    _ = membership
    controller = TemplateController(service=TemplateService())
    return await controller.extract_schema_from_upload(file)


@router.post(
    "/import/analyze",
    response_model=TemplateImportAnalysisResponse,
    status_code=status.HTTP_200_OK,
)
async def analyze_template_import_upload(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
) -> TemplateImportAnalysisResponse:
    """Analyze a regular DOCX upload and return likely import bindings."""
    membership = require_template_write_access(current_user, request=request)
    _ = membership
    controller = TemplateController(service=TemplateService())
    return await controller.analyze_import_from_upload(file)


@router.post(
    "/import/inspect",
    response_model=TemplateImportInspectionResponse,
    status_code=status.HTTP_200_OK,
)
async def inspect_template_import_upload(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
) -> TemplateImportInspectionResponse:
    """Inspect a DOCX upload for assisted templateization."""
    membership = require_template_write_access(current_user, request=request)
    _ = membership
    controller = TemplateController(service=TemplateService())
    return await controller.inspect_import_from_upload(file)


@router.get("/{template_id}", response_model=TemplateDetailResponse)
async def get_template(
    request: Request,
    template_id: UUID,
    query: Annotated[TemplateAccessQuery, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TemplateDetailResponse:
    """Return one template with its current version details."""
    require_template_read_access(current_user, query.organization_id, request=request)
    controller = TemplateController(service=TemplateService())
    return await controller.get_template(
        organization_id=query.organization_id,
        template_id=template_id,
    )


@router.post(
    "/{template_id}/import/analyze",
    response_model=TemplateImportAnalysisResponse,
    status_code=status.HTTP_200_OK,
)
async def analyze_stored_template_import(
    request: Request,
    template_id: UUID,
    payload: TemplateImportAnalyzeStoredRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> TemplateImportAnalysisResponse:
    """Analyze the current stored template version as an imported DOCX source."""
    require_template_write_access(current_user, payload.organization_id, request=request)
    controller = TemplateController(service=TemplateService())
    return await controller.analyze_import_for_template(
        organization_id=payload.organization_id,
        template_id=template_id,
    )


@router.post(
    "/{template_id}/import/inspect",
    response_model=TemplateImportInspectionResponse,
    status_code=status.HTTP_200_OK,
)
async def inspect_stored_template_import(
    request: Request,
    template_id: UUID,
    payload: TemplateImportAnalyzeStoredRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> TemplateImportInspectionResponse:
    """Inspect the current stored template version for assisted templateization."""
    require_template_write_access(current_user, payload.organization_id, request=request)
    controller = TemplateController(service=TemplateService())
    return await controller.inspect_import_for_template(
        organization_id=payload.organization_id,
        template_id=template_id,
    )


@router.post(
    "/{template_id}/import/confirm",
    response_model=TemplateImportConfirmationResponse,
    status_code=status.HTTP_200_OK,
)
async def confirm_stored_template_import(
    request: Request,
    template_id: UUID,
    payload: TemplateImportConfirmRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> TemplateImportConfirmationResponse:
    """Persist confirmed bindings for an imported DOCX template."""
    require_template_write_access(current_user, payload.organization_id, request=request)
    controller = TemplateController(service=TemplateService())
    return await controller.confirm_import_for_template(
        organization_id=payload.organization_id,
        template_id=template_id,
        payload=payload,
    )


@router.post(
    "/{template_id}/import/templateize",
    response_model=TemplateTemplateizationConfirmationResponse,
    status_code=status.HTTP_200_OK,
)
async def templateize_stored_template_import(
    request: Request,
    template_id: UUID,
    payload: TemplateImportTemplateizeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> TemplateTemplateizationConfirmationResponse:
    """Persist manual paragraph-span selections for assisted templateization."""
    require_template_write_access(current_user, payload.organization_id, request=request)
    controller = TemplateController(service=TemplateService())
    return await controller.templateize_import_for_template(
        organization_id=payload.organization_id,
        template_id=template_id,
        payload=payload,
    )


@router.post(
    "/{template_id}/extract-schema",
    response_model=TemplateSchemaExtractionResponse,
    status_code=status.HTTP_200_OK,
)
async def extract_stored_template_schema(
    request: Request,
    template_id: UUID,
    query: Annotated[TemplateAccessQuery, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TemplateSchemaExtractionResponse:
    """Re-extract schema from the current stored template version."""
    require_template_write_access(current_user, query.organization_id, request=request)
    controller = TemplateController(service=TemplateService())
    return await controller.extract_schema_for_template(
        organization_id=query.organization_id,
        template_id=template_id,
    )
