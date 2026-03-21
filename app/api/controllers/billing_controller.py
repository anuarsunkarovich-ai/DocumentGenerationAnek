"""Controller helpers for billing endpoints."""

from app.dtos.billing import (
    BillingCycleRunResponse,
    BillingInvoiceListResponse,
    BillingInvoiceResponse,
    BillingPlanListResponse,
    BillingPlanResponse,
    BillingSnapshotResponse,
    BillingSubscriptionResponse,
    BillingUsageMeterResponse,
)
from app.services.billing_service import BillingService


class BillingController:
    """Coordinate billing plan, snapshot, and invoice requests."""

    def __init__(self, service: BillingService) -> None:
        self._service = service

    async def list_plans(self, *, organization_id) -> BillingPlanListResponse:
        """Return the active plan catalog."""
        _ = organization_id
        plans = await self._service.list_plans()
        return BillingPlanListResponse(items=[self._build_plan_response(plan) for plan in plans])

    async def get_snapshot(self, *, organization_id) -> BillingSnapshotResponse:
        """Return current billing state for one organization."""
        snapshot = await self._service.get_billing_snapshot(organization_id=organization_id)
        return BillingSnapshotResponse(
            subscription=BillingSubscriptionResponse(
                organization_id=snapshot.subscription.organization_id,
                status=snapshot.subscription.status,
                current_period_start=snapshot.subscription.current_period_start,
                current_period_end=snapshot.subscription.current_period_end,
                plan=self._build_plan_response(snapshot.plan),
                pending_plan=(
                    self._build_plan_response(snapshot.subscription.pending_plan)
                    if snapshot.subscription.pending_plan is not None
                    else None
                ),
            ),
            usage_meter=BillingUsageMeterResponse.model_validate(snapshot.usage_meter),
        )

    async def list_invoices(self, *, organization_id, limit: int) -> BillingInvoiceListResponse:
        """Return recent invoices for one organization."""
        invoices = await self._service.list_invoices(organization_id=organization_id, limit=limit)
        return BillingInvoiceListResponse(
            items=[BillingInvoiceResponse.model_validate(invoice) for invoice in invoices]
        )

    async def schedule_plan_change(self, *, organization_id, target_plan_code: str) -> BillingSnapshotResponse:
        """Schedule a plan change for the next renewal boundary."""
        snapshot = await self._service.schedule_plan_change(
            organization_id=organization_id,
            target_plan_code=target_plan_code,
        )
        return BillingSnapshotResponse(
            subscription=BillingSubscriptionResponse(
                organization_id=snapshot.subscription.organization_id,
                status=snapshot.subscription.status,
                current_period_start=snapshot.subscription.current_period_start,
                current_period_end=snapshot.subscription.current_period_end,
                plan=self._build_plan_response(snapshot.plan),
                pending_plan=(
                    self._build_plan_response(snapshot.subscription.pending_plan)
                    if snapshot.subscription.pending_plan is not None
                    else None
                ),
            ),
            usage_meter=BillingUsageMeterResponse.model_validate(snapshot.usage_meter),
        )

    async def run_billing_cycle(self, *, organization_id) -> BillingCycleRunResponse:
        """Finalize due invoices for one organization immediately."""
        result = await self._service.run_billing_cycle(organization_id=organization_id)
        return BillingCycleRunResponse(
            finalized_invoice_count=result.finalized_invoice_count,
            renewed_subscription_count=result.renewed_subscription_count,
            billed_organization_ids=result.billed_organization_ids,
        )

    def _build_plan_response(self, plan) -> BillingPlanResponse:
        return BillingPlanResponse.model_validate(plan)
