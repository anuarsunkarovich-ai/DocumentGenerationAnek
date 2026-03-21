"""Internal admin routes for billing plans and invoices."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.controllers.billing_controller import BillingController
from app.api.dependencies.auth import get_current_user
from app.api.dependencies.authorization import require_audit_access
from app.dtos.billing import (
    BillingAccessQuery,
    BillingCycleRunRequest,
    BillingCycleRunResponse,
    BillingInvoiceListQuery,
    BillingInvoiceListResponse,
    BillingPlanChangeRequest,
    BillingPlanListResponse,
    BillingSnapshotResponse,
)
from app.models.user import User
from app.services.billing_service import BillingService

router = APIRouter(prefix="/admin/billing", tags=["billing"])


@router.get("/plans", response_model=BillingPlanListResponse)
async def list_billing_plans(
    query: Annotated[BillingAccessQuery, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
) -> BillingPlanListResponse:
    """Return the active commercial plan catalog."""
    require_audit_access(current_user, query.organization_id)
    controller = BillingController(service=BillingService())
    return await controller.list_plans(organization_id=query.organization_id)


@router.get("/snapshot", response_model=BillingSnapshotResponse)
async def get_billing_snapshot(
    query: Annotated[BillingAccessQuery, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
) -> BillingSnapshotResponse:
    """Return current billing state for one organization."""
    require_audit_access(current_user, query.organization_id)
    controller = BillingController(service=BillingService())
    return await controller.get_snapshot(organization_id=query.organization_id)


@router.get("/invoices", response_model=BillingInvoiceListResponse)
async def list_billing_invoices(
    query: Annotated[BillingInvoiceListQuery, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
) -> BillingInvoiceListResponse:
    """Return recent invoice history for one organization."""
    require_audit_access(current_user, query.organization_id)
    controller = BillingController(service=BillingService())
    return await controller.list_invoices(
        organization_id=query.organization_id,
        limit=query.limit,
    )


@router.post("/subscription/change", response_model=BillingSnapshotResponse)
async def schedule_billing_plan_change(
    payload: BillingPlanChangeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> BillingSnapshotResponse:
    """Schedule a billing plan change for the next renewal."""
    require_audit_access(current_user, payload.organization_id)
    controller = BillingController(service=BillingService())
    return await controller.schedule_plan_change(
        organization_id=payload.organization_id,
        target_plan_code=payload.target_plan_code,
    )


@router.post("/cycle/run", response_model=BillingCycleRunResponse)
async def run_billing_cycle(
    payload: BillingCycleRunRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> BillingCycleRunResponse:
    """Trigger a manual invoice finalization pass for one organization."""
    require_audit_access(current_user, payload.organization_id)
    controller = BillingController(service=BillingService())
    return await controller.run_billing_cycle(organization_id=payload.organization_id)
