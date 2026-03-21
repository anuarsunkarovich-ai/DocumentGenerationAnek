"""Plan assignment, monthly metering, invoice generation, and billing automation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from inspect import isawaitable
from typing import Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_transaction_session
from app.core.exceptions import ConflictError, NotFoundError
from app.dtos.constructor import DocumentConstructor
from app.models.billing_invoice import BillingInvoice
from app.models.organization_plan import OrganizationPlan
from app.models.organization_usage_meter import OrganizationUsageMeter
from app.models.plan_definition import PlanDefinition
from app.repositories.billing_invoice_repository import BillingInvoiceRepository
from app.repositories.document_artifact_repository import DocumentArtifactRepository
from app.repositories.organization_plan_repository import OrganizationPlanRepository
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.organization_usage_meter_repository import OrganizationUsageMeterRepository
from app.repositories.plan_definition_repository import PlanDefinitionRepository
from app.repositories.template_repository import TemplateRepository
from app.repositories.template_version_repository import TemplateVersionRepository
from app.repositories.user_repository import UserRepository


@dataclass(frozen=True)
class BillingSnapshot:
    """Resolved plan and usage context for one organization-period."""

    plan: PlanDefinition
    subscription: OrganizationPlan
    usage_meter: OrganizationUsageMeter


@dataclass(frozen=True)
class BillingCycleRunResult:
    """Summary of one automated billing-cycle pass."""

    finalized_invoice_count: int = 0
    renewed_subscription_count: int = 0
    billed_organization_ids: list[UUID] = field(default_factory=list)


class BillingService:
    """Manage plan defaults, monthly meters, invoices, and business-limit checks."""

    DEFAULT_PLAN_CODE = "starter"
    SIGNATURE_FEATURE_KEY = "signature_requests"
    PAYMENT_TERMS_DAYS = 7

    async def list_plans(self, *, session: AsyncSession | None = None) -> list[PlanDefinition]:
        """Return the active plan catalog."""
        if session is not None:
            return await PlanDefinitionRepository(session).list_active()

        async with get_transaction_session() as managed_session:
            return await PlanDefinitionRepository(managed_session).list_active()

    async def enforce_generation_allowed(
        self,
        *,
        organization_id: UUID,
        constructor: DocumentConstructor,
        session: AsyncSession | None = None,
    ) -> None:
        """Reject generation requests that exceed plan limits."""
        snapshot = await self._with_snapshot(
            organization_id=organization_id,
            session=session,
            action=lambda resolved_session, billing_snapshot: self._enforce_generation_allowed(
                resolved_session,
                billing_snapshot,
                constructor=constructor,
            ),
        )
        _ = snapshot

    async def record_generation_request(
        self,
        *,
        organization_id: UUID,
        constructor: DocumentConstructor,
        session: AsyncSession | None = None,
    ) -> None:
        """Record one accepted generation request and premium feature usage."""
        await self._with_snapshot(
            organization_id=organization_id,
            session=session,
            action=lambda resolved_session, billing_snapshot: self._record_generation_request(
                resolved_session,
                billing_snapshot,
                constructor=constructor,
            ),
        )

    async def enforce_template_creation_allowed(
        self,
        *,
        organization_id: UUID,
        session: AsyncSession | None = None,
    ) -> None:
        """Reject template creation when the current plan template cap is exhausted."""
        await self._with_snapshot(
            organization_id=organization_id,
            session=session,
            action=self._enforce_template_creation_allowed,
        )

    async def enforce_storage_delta_allowed(
        self,
        *,
        organization_id: UUID,
        additional_bytes: int,
        session: AsyncSession | None = None,
    ) -> None:
        """Reject storage-expanding operations that exceed quota."""
        await self._with_snapshot(
            organization_id=organization_id,
            session=session,
            action=lambda resolved_session, billing_snapshot: self._enforce_storage_delta_allowed(
                resolved_session,
                billing_snapshot,
                additional_bytes=additional_bytes,
            ),
        )

    async def record_storage_usage(
        self,
        *,
        organization_id: UUID,
        delta_bytes: int,
        session: AsyncSession | None = None,
    ) -> None:
        """Adjust measured storage usage after template or artifact writes."""
        await self._with_snapshot(
            organization_id=organization_id,
            session=session,
            action=lambda resolved_session, billing_snapshot: self._record_storage_usage(
                resolved_session,
                billing_snapshot,
                delta_bytes=delta_bytes,
            ),
        )

    async def sync_template_count(
        self,
        *,
        organization_id: UUID,
        session: AsyncSession | None = None,
    ) -> int:
        """Refresh the tracked template count from current database state."""
        return await self._with_snapshot(
            organization_id=organization_id,
            session=session,
            action=self._sync_template_count,
        )

    async def get_audit_retention_days(
        self,
        *,
        organization_id: UUID,
        session: AsyncSession | None = None,
    ) -> int:
        """Return the audit retention window for the current plan."""
        return await self._with_snapshot(
            organization_id=organization_id,
            session=session,
            action=lambda resolved_session, billing_snapshot: billing_snapshot.plan.audit_retention_days,
        )

    async def get_billing_snapshot(
        self,
        *,
        organization_id: UUID,
        session: AsyncSession | None = None,
    ) -> BillingSnapshot:
        """Return current plan and meter state for one organization."""
        return await self._with_snapshot(
            organization_id=organization_id,
            session=session,
            action=self._refresh_snapshot_usage,
        )

    async def list_invoices(
        self,
        *,
        organization_id: UUID,
        limit: int = 25,
        session: AsyncSession | None = None,
    ) -> list[BillingInvoice]:
        """Return recent invoices for one organization."""
        if session is not None:
            return await BillingInvoiceRepository(session).list_for_organization(
                organization_id=organization_id,
                limit=limit,
            )

        async with get_transaction_session() as managed_session:
            return await BillingInvoiceRepository(managed_session).list_for_organization(
                organization_id=organization_id,
                limit=limit,
            )

    async def schedule_plan_change(
        self,
        *,
        organization_id: UUID,
        target_plan_code: str,
        session: AsyncSession | None = None,
    ) -> BillingSnapshot:
        """Queue a plan change for the next renewal boundary."""
        normalized_plan_code = target_plan_code.strip().lower()
        if not normalized_plan_code:
            raise NotFoundError("Target billing plan was not found.")

        if session is not None:
            return await self._schedule_plan_change(
                session,
                organization_id=organization_id,
                target_plan_code=normalized_plan_code,
            )

        async with get_transaction_session() as managed_session:
            return await self._schedule_plan_change(
                managed_session,
                organization_id=organization_id,
                target_plan_code=normalized_plan_code,
            )

    async def run_billing_cycle(
        self,
        *,
        organization_id: UUID | None = None,
        as_of: date | None = None,
        session: AsyncSession | None = None,
    ) -> BillingCycleRunResult:
        """Finalize ended billing periods and roll subscriptions into the next cycle."""
        billing_date = as_of or datetime.now(timezone.utc).date()
        if session is not None:
            return await self._run_billing_cycle(session, organization_id=organization_id, as_of=billing_date)

        async with get_transaction_session() as managed_session:
            return await self._run_billing_cycle(
                managed_session,
                organization_id=organization_id,
                as_of=billing_date,
            )

    async def _with_snapshot(
        self,
        *,
        organization_id: UUID,
        session: AsyncSession | None,
        action: Callable[[AsyncSession, BillingSnapshot], object],
    ):
        if session is not None:
            snapshot = await self._ensure_snapshot(session, organization_id=organization_id)
            result = action(session, snapshot)
            if isawaitable(result):
                return await result
            return result

        async with get_transaction_session() as managed_session:
            snapshot = await self._ensure_snapshot(managed_session, organization_id=organization_id)
            result = action(managed_session, snapshot)
            if isawaitable(result):
                return await result
            return result

    async def _ensure_snapshot(
        self,
        session: AsyncSession,
        *,
        organization_id: UUID,
    ) -> BillingSnapshot:
        organization = await OrganizationRepository(session).get_by_id(organization_id)
        if organization is None:
            raise NotFoundError("Organization was not found.")

        plan_repository = PlanDefinitionRepository(session)
        subscription_repository = OrganizationPlanRepository(session)
        usage_repository = OrganizationUsageMeterRepository(session)

        subscription = await subscription_repository.get_by_organization_id(organization_id)
        if subscription is None:
            default_plan = await plan_repository.get_by_code(self.DEFAULT_PLAN_CODE)
            if default_plan is None:
                raise NotFoundError("Default billing plan was not found.")
            period_start, period_end = self._current_period_bounds()
            await subscription_repository.create(
                OrganizationPlan(
                    organization_id=organization_id,
                    plan_definition_id=default_plan.id,
                    pending_plan_definition_id=None,
                    status="active",
                    current_period_start=period_start,
                    current_period_end=period_end,
                )
            )
            subscription = await subscription_repository.get_by_organization_id(organization_id)
            if subscription is None:
                raise NotFoundError("Organization billing plan was not created.")
        else:
            subscription, _ = await self._roll_subscription_forward_if_needed(session, subscription)

        usage_meter = await usage_repository.get_by_period(
            organization_id=organization_id,
            period_start=subscription.current_period_start,
        )
        if usage_meter is None:
            usage_meter = await usage_repository.create(
                OrganizationUsageMeter(
                    organization_id=organization_id,
                    period_start=subscription.current_period_start,
                    period_end=subscription.current_period_end,
                    generation_count=0,
                    storage_bytes=await self._current_storage_bytes(session, organization_id),
                    template_count=await TemplateRepository(session).count_by_organization(organization_id),
                    user_count=await UserRepository(session).count_active_for_organization(organization_id),
                    premium_feature_usage={},
                )
            )

        return BillingSnapshot(
            plan=subscription.plan,
            subscription=subscription,
            usage_meter=usage_meter,
        )

    async def _enforce_generation_allowed(
        self,
        session: AsyncSession,
        snapshot: BillingSnapshot,
        *,
        constructor: DocumentConstructor,
    ) -> None:
        _ = session
        if snapshot.usage_meter.generation_count >= snapshot.plan.monthly_generation_cap:
            raise ConflictError("Monthly document generation cap exceeded for the current plan.")
        if self._signature_block_count(constructor) > 0 and not snapshot.plan.signature_support:
            raise ConflictError("Signature blocks are not available on the current plan.")

    async def _record_generation_request(
        self,
        session: AsyncSession,
        snapshot: BillingSnapshot,
        *,
        constructor: DocumentConstructor,
    ) -> None:
        usage_repository = OrganizationUsageMeterRepository(session)
        await usage_repository.increment_generation(snapshot.usage_meter)
        signature_block_count = self._signature_block_count(constructor)
        if signature_block_count > 0:
            await usage_repository.increment_premium_feature(
                snapshot.usage_meter,
                feature_key=self.SIGNATURE_FEATURE_KEY,
                amount=signature_block_count,
            )

    async def _enforce_template_creation_allowed(
        self,
        session: AsyncSession,
        snapshot: BillingSnapshot,
    ) -> None:
        template_count = await self._sync_template_count(session, snapshot)
        if template_count >= snapshot.plan.max_templates:
            raise ConflictError("Template limit exceeded for the current plan.")

    async def _enforce_storage_delta_allowed(
        self,
        session: AsyncSession,
        snapshot: BillingSnapshot,
        *,
        additional_bytes: int,
    ) -> None:
        _ = session
        if additional_bytes <= 0:
            return
        projected_storage = snapshot.usage_meter.storage_bytes + additional_bytes
        if projected_storage > snapshot.plan.storage_quota_bytes:
            raise ConflictError("Storage quota exceeded for the current plan.")

    async def _record_storage_usage(
        self,
        session: AsyncSession,
        snapshot: BillingSnapshot,
        *,
        delta_bytes: int,
    ) -> None:
        await OrganizationUsageMeterRepository(session).adjust_storage_bytes(
            snapshot.usage_meter,
            delta_bytes=delta_bytes,
        )

    async def _sync_template_count(
        self,
        session: AsyncSession,
        snapshot: BillingSnapshot,
    ) -> int:
        template_count = await TemplateRepository(session).count_by_organization(
            snapshot.subscription.organization_id
        )
        await OrganizationUsageMeterRepository(session).set_template_count(
            snapshot.usage_meter,
            template_count=template_count,
        )
        return template_count

    async def _sync_user_count(
        self,
        session: AsyncSession,
        snapshot: BillingSnapshot,
    ) -> int:
        user_count = await UserRepository(session).count_active_for_organization(
            snapshot.subscription.organization_id
        )
        await OrganizationUsageMeterRepository(session).set_user_count(
            snapshot.usage_meter,
            user_count=user_count,
        )
        return user_count

    async def _refresh_snapshot_usage(
        self,
        session: AsyncSession,
        snapshot: BillingSnapshot,
    ) -> BillingSnapshot:
        await self._sync_template_count(session, snapshot)
        await self._sync_user_count(session, snapshot)
        return snapshot

    async def _schedule_plan_change(
        self,
        session: AsyncSession,
        *,
        organization_id: UUID,
        target_plan_code: str,
    ) -> BillingSnapshot:
        snapshot = await self._ensure_snapshot(session, organization_id=organization_id)
        target_plan = await PlanDefinitionRepository(session).get_by_code(target_plan_code)
        if target_plan is None or not target_plan.is_active:
            raise NotFoundError("Target billing plan was not found.")

        if snapshot.subscription.plan_definition_id == target_plan.id:
            if snapshot.subscription.pending_plan_definition_id is None:
                return await self._refresh_snapshot_usage(session, snapshot)
            await OrganizationPlanRepository(session).schedule_plan_change(
                snapshot.subscription,
                pending_plan_definition_id=target_plan.id,
            )
            return await self._ensure_snapshot(session, organization_id=organization_id)

        await OrganizationPlanRepository(session).schedule_plan_change(
            snapshot.subscription,
            pending_plan_definition_id=target_plan.id,
        )
        return await self._ensure_snapshot(session, organization_id=organization_id)

    async def _run_billing_cycle(
        self,
        session: AsyncSession,
        *,
        organization_id: UUID | None,
        as_of: date,
    ) -> BillingCycleRunResult:
        subscription_repository = OrganizationPlanRepository(session)
        if organization_id is not None:
            subscription = await subscription_repository.get_by_organization_id(organization_id)
            if subscription is None:
                return BillingCycleRunResult()
            subscription, invoice_count = await self._roll_subscription_forward_if_needed(
                session,
                subscription,
                as_of=as_of,
            )
            renewed_count = invoice_count
            billed_organization_ids = [organization_id] if invoice_count else []
            _ = subscription
            return BillingCycleRunResult(
                finalized_invoice_count=invoice_count,
                renewed_subscription_count=renewed_count,
                billed_organization_ids=billed_organization_ids,
            )

        due_subscriptions = await subscription_repository.list_due_for_renewal(as_of=as_of)
        billed_organization_ids: list[UUID] = []
        invoice_count = 0
        renewed_count = 0
        for subscription in due_subscriptions:
            updated_subscription, created_invoices = await self._roll_subscription_forward_if_needed(
                session,
                subscription,
                as_of=as_of,
            )
            _ = updated_subscription
            if created_invoices > 0:
                billed_organization_ids.append(subscription.organization_id)
                invoice_count += created_invoices
                renewed_count += created_invoices

        return BillingCycleRunResult(
            finalized_invoice_count=invoice_count,
            renewed_subscription_count=renewed_count,
            billed_organization_ids=billed_organization_ids,
        )

    async def _roll_subscription_forward_if_needed(
        self,
        session: AsyncSession,
        subscription: OrganizationPlan,
        *,
        as_of: date | None = None,
    ) -> tuple[OrganizationPlan, int]:
        billing_date = as_of or datetime.now(timezone.utc).date()
        if subscription.current_period_end > billing_date:
            return subscription, 0

        repository = OrganizationPlanRepository(session)
        invoice_count = 0
        current_subscription = subscription
        while current_subscription.current_period_end <= billing_date:
            await self._issue_invoice_for_period(session, current_subscription)
            invoice_count += 1
            next_period_start = current_subscription.current_period_end
            next_period_end = self._next_period_end(next_period_start)
            next_plan_definition_id = (
                current_subscription.pending_plan_definition_id
                or current_subscription.plan_definition_id
            )
            current_subscription = await repository.update_period(
                current_subscription,
                period_start=next_period_start,
                period_end=next_period_end,
                plan_definition_id=next_plan_definition_id,
                pending_plan_definition_id=None,
            )
            current_subscription = await repository.get_by_organization_id(
                current_subscription.organization_id
            )
            if current_subscription is None:
                raise NotFoundError("Organization billing plan was not found after renewal.")

        return current_subscription, invoice_count

    async def _issue_invoice_for_period(
        self,
        session: AsyncSession,
        subscription: OrganizationPlan,
    ) -> BillingInvoice:
        invoice_repository = BillingInvoiceRepository(session)
        existing_invoice = await invoice_repository.get_by_period(
            organization_id=subscription.organization_id,
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
        )
        if existing_invoice is not None:
            return existing_invoice

        usage_summary = await self._resolve_usage_summary_for_period(session, subscription)
        issued_at = datetime.now(timezone.utc)
        subtotal_cents = int(subscription.plan.monthly_price_cents)
        return await invoice_repository.create(
            BillingInvoice(
                organization_id=subscription.organization_id,
                organization_plan_id=subscription.id,
                plan_definition_id=subscription.plan_definition_id,
                plan_code=subscription.plan.code,
                currency_code=subscription.plan.currency_code,
                status="issued",
                period_start=subscription.current_period_start,
                period_end=subscription.current_period_end,
                subtotal_cents=subtotal_cents,
                generation_count=usage_summary.generation_count,
                template_count=usage_summary.template_count,
                user_count=usage_summary.user_count,
                storage_bytes=usage_summary.storage_bytes,
                premium_feature_usage=dict(usage_summary.premium_feature_usage or {}),
                line_items=[
                    {
                        "code": "base_plan",
                        "description": f"{subscription.plan.name} monthly organization subscription",
                        "quantity": 1,
                        "unit_amount_cents": subtotal_cents,
                        "subtotal_cents": subtotal_cents,
                        "currency_code": subscription.plan.currency_code,
                    }
                ],
                issued_at=issued_at,
                due_at=issued_at + timedelta(days=self.PAYMENT_TERMS_DAYS),
            )
        )

    async def _resolve_usage_summary_for_period(
        self,
        session: AsyncSession,
        subscription: OrganizationPlan,
    ) -> OrganizationUsageMeter:
        usage_repository = OrganizationUsageMeterRepository(session)
        usage_meter = await usage_repository.get_by_period(
            organization_id=subscription.organization_id,
            period_start=subscription.current_period_start,
        )
        if usage_meter is not None:
            return usage_meter

        return OrganizationUsageMeter(
            organization_id=subscription.organization_id,
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            generation_count=0,
            storage_bytes=await self._current_storage_bytes(session, subscription.organization_id),
            template_count=await TemplateRepository(session).count_by_organization(
                subscription.organization_id
            ),
            user_count=await UserRepository(session).count_active_for_organization(
                subscription.organization_id
            ),
            premium_feature_usage={},
        )

    async def _current_storage_bytes(self, session: AsyncSession, organization_id: UUID) -> int:
        template_bytes = await TemplateVersionRepository(session).sum_storage_bytes_for_organization(
            organization_id
        )
        artifact_bytes = await DocumentArtifactRepository(session).sum_storage_bytes_for_organization(
            organization_id
        )
        return template_bytes + artifact_bytes

    def _signature_block_count(self, constructor: DocumentConstructor) -> int:
        return sum(1 for block in constructor.blocks if getattr(block, "type", None) == "signature")

    def _current_period_bounds(self) -> tuple[date, date]:
        now = datetime.now(timezone.utc)
        period_start = date(now.year, now.month, 1)
        return period_start, self._next_period_end(period_start)

    def _next_period_end(self, period_start: date) -> date:
        if period_start.month == 12:
            return date(period_start.year + 1, 1, 1)
        return date(period_start.year, period_start.month + 1, 1)
