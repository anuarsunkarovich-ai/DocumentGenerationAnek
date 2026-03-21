"""DTOs for billing plans, subscriptions, and invoice history."""

from datetime import date, datetime
from uuid import UUID

from pydantic import Field, field_validator

from app.dtos.common import BaseDTO


class BillingAccessQuery(BaseDTO):
    """Tenant-scoped query for billing endpoints."""

    organization_id: UUID


class BillingInvoiceListQuery(BaseDTO):
    """Tenant-scoped invoice history query."""

    organization_id: UUID
    limit: int = Field(default=25, ge=1, le=100)


class BillingPlanChangeRequest(BaseDTO):
    """Schedule a new plan for the selected organization."""

    organization_id: UUID
    target_plan_code: str = Field(min_length=1, max_length=50)

    @field_validator("target_plan_code")
    @classmethod
    def normalize_target_plan_code(cls, value: str) -> str:
        """Normalize plan codes before persistence."""
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("Target plan code cannot be empty.")
        return normalized


class BillingCycleRunRequest(BaseDTO):
    """Trigger one manual billing cycle pass for the selected organization."""

    organization_id: UUID


class BillingPlanResponse(BaseDTO):
    """Commercial plan response."""

    id: UUID
    code: str
    name: str
    billable_unit: str
    monthly_generation_cap: int
    max_templates: int
    max_users: int
    storage_quota_bytes: int
    monthly_price_cents: int
    currency_code: str
    audit_retention_days: int
    signature_support: bool
    is_active: bool


class BillingUsageMeterResponse(BaseDTO):
    """Meter summary for the active billing period."""

    period_start: date
    period_end: date
    generation_count: int
    storage_bytes: int
    template_count: int
    user_count: int
    premium_feature_usage: dict = Field(default_factory=dict)


class BillingSubscriptionResponse(BaseDTO):
    """Organization billing subscription summary."""

    organization_id: UUID
    status: str
    current_period_start: date
    current_period_end: date
    plan: BillingPlanResponse
    pending_plan: BillingPlanResponse | None = None


class BillingSnapshotResponse(BaseDTO):
    """Current subscription and usage state for one organization."""

    subscription: BillingSubscriptionResponse
    usage_meter: BillingUsageMeterResponse


class BillingPlanListResponse(BaseDTO):
    """List of active plans."""

    items: list[BillingPlanResponse] = Field(default_factory=list)


class BillingInvoiceResponse(BaseDTO):
    """One finalized invoice."""

    id: UUID
    organization_id: UUID
    organization_plan_id: UUID
    plan_definition_id: UUID
    plan_code: str
    currency_code: str
    status: str
    period_start: date
    period_end: date
    subtotal_cents: int
    generation_count: int
    template_count: int
    user_count: int
    storage_bytes: int
    premium_feature_usage: dict = Field(default_factory=dict)
    line_items: list[dict] = Field(default_factory=list)
    issued_at: datetime
    due_at: datetime
    paid_at: datetime | None = None
    created_at: datetime


class BillingInvoiceListResponse(BaseDTO):
    """Recent invoices for one organization."""

    items: list[BillingInvoiceResponse] = Field(default_factory=list)


class BillingCycleRunResponse(BaseDTO):
    """Summary of one manual or scheduled billing-cycle run."""

    finalized_invoice_count: int
    renewed_subscription_count: int
    billed_organization_ids: list[UUID] = Field(default_factory=list)
