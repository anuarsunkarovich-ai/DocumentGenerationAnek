"""Plan assignment, monthly metering, and service-boundary enforcement."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from inspect import isawaitable
from typing import Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_transaction_session
from app.core.exceptions import ConflictError, NotFoundError
from app.dtos.constructor import DocumentConstructor
from app.models.organization_plan import OrganizationPlan
from app.models.organization_usage_meter import OrganizationUsageMeter
from app.models.plan_definition import PlanDefinition
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


class BillingService:
    """Manage plan defaults, monthly meters, and business-limit checks."""

    DEFAULT_PLAN_CODE = "starter"
    SIGNATURE_FEATURE_KEY = "signature_requests"

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
            action=lambda resolved_session, billing_snapshot: billing_snapshot,
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

        period_start, period_end = self._current_period_bounds()
        plan_repository = PlanDefinitionRepository(session)
        subscription_repository = OrganizationPlanRepository(session)
        usage_repository = OrganizationUsageMeterRepository(session)

        subscription = await subscription_repository.get_by_organization_id(organization_id)
        if subscription is None:
            default_plan = await plan_repository.get_by_code(self.DEFAULT_PLAN_CODE)
            if default_plan is None:
                raise NotFoundError("Default billing plan was not found.")
            subscription = await subscription_repository.create(
                OrganizationPlan(
                    organization_id=organization_id,
                    plan_definition_id=default_plan.id,
                    status="active",
                    current_period_start=period_start,
                    current_period_end=period_end,
                )
            )
            subscription = await subscription_repository.get_by_organization_id(organization_id)
            if subscription is None:
                raise NotFoundError("Organization billing plan was not created.")
        elif subscription.current_period_start != period_start or subscription.current_period_end != period_end:
            subscription = await subscription_repository.update_period(
                subscription,
                period_start=period_start,
                period_end=period_end,
            )

        plan = subscription.plan
        usage_meter = await usage_repository.get_by_period(
            organization_id=organization_id,
            period_start=period_start,
        )
        if usage_meter is None:
            usage_meter = await usage_repository.create(
                OrganizationUsageMeter(
                    organization_id=organization_id,
                    period_start=period_start,
                    period_end=period_end,
                    generation_count=0,
                    storage_bytes=await self._current_storage_bytes(session, organization_id),
                    template_count=await TemplateRepository(session).count_by_organization(organization_id),
                    user_count=await UserRepository(session).count_active_for_organization(organization_id),
                    premium_feature_usage={},
                )
            )

        return BillingSnapshot(
            plan=plan,
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
        if now.month == 12:
            period_end = date(now.year + 1, 1, 1)
        else:
            period_end = date(now.year, now.month + 1, 1)
        return period_start, period_end
