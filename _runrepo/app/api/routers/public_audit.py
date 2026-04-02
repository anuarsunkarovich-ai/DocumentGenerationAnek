"""Public machine-auth routes for audit reads."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.controllers.admin_controller import AdminController
from app.api.dependencies.api_keys import require_api_key_scope
from app.dtos.admin import AuditEventListResponse
from app.dtos.api_key import ApiKeyScope
from app.services.api_key_service import ApiKeyPrincipal
from app.services.operations_service import OperationsService

router = APIRouter(prefix="/public/audit", tags=["public-audit"])


@router.get("/events", response_model=AuditEventListResponse)
async def list_public_audit_events(
    principal: Annotated[
        ApiKeyPrincipal,
        Depends(require_api_key_scope(ApiKeyScope.AUDIT_READ)),
    ],
) -> AuditEventListResponse:
    """Return recent audit events for the API key's organization."""
    controller = AdminController(service=OperationsService())
    return await controller.list_recent_audit_events(
        organization_id=principal.organization_id,
        limit=25,
    )
