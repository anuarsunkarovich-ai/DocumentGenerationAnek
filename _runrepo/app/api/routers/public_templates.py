"""Public machine-auth routes for published template reads."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.controllers.template_controller import TemplateController
from app.api.dependencies.api_keys import require_api_key_scope
from app.dtos.api_key import ApiKeyScope
from app.dtos.template import TemplateDetailResponse, TemplateListResponse
from app.services.api_key_service import ApiKeyPrincipal
from app.services.template_service import TemplateService

router = APIRouter(prefix="/public/templates", tags=["public-templates"])


@router.get("", response_model=TemplateListResponse)
async def list_public_templates(
    principal: Annotated[
        ApiKeyPrincipal,
        Depends(require_api_key_scope(ApiKeyScope.TEMPLATES_READ)),
    ],
) -> TemplateListResponse:
    """Return published templates visible to the API key's organization."""
    controller = TemplateController(service=TemplateService())
    return await controller.list_templates(
        principal.organization_id,
        published_only=True,
    )


@router.get("/{template_id}", response_model=TemplateDetailResponse)
async def get_public_template(
    template_id: UUID,
    principal: Annotated[
        ApiKeyPrincipal,
        Depends(require_api_key_scope(ApiKeyScope.TEMPLATES_READ)),
    ],
) -> TemplateDetailResponse:
    """Return one published template detail for the API key's organization."""
    controller = TemplateController(service=TemplateService())
    return await controller.get_template(
        organization_id=principal.organization_id,
        template_id=template_id,
        published_only=True,
    )
