"""Repository for organization plan assignments."""

from datetime import date
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.organization_plan import OrganizationPlan


class OrganizationPlanRepository:
    """Access current plan assignments for organizations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_organization_id(self, organization_id: UUID) -> OrganizationPlan | None:
        """Return the current plan assignment for one organization."""
        statement: Select[tuple[OrganizationPlan]] = (
            select(OrganizationPlan)
            .options(
                selectinload(OrganizationPlan.plan),
                selectinload(OrganizationPlan.pending_plan),
            )
            .where(OrganizationPlan.organization_id == organization_id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def create(self, organization_plan: OrganizationPlan) -> OrganizationPlan:
        """Persist one plan assignment."""
        self._session.add(organization_plan)
        await self._session.flush()
        await self._session.refresh(organization_plan)
        return organization_plan

    async def update_period(
        self,
        organization_plan: OrganizationPlan,
        *,
        period_start: date,
        period_end: date,
        plan_definition_id: UUID | None = None,
        pending_plan_definition_id: UUID | None = None,
    ) -> OrganizationPlan:
        """Roll one organization into a new billing period."""
        if plan_definition_id is not None:
            organization_plan.plan_definition_id = plan_definition_id
        organization_plan.pending_plan_definition_id = pending_plan_definition_id
        organization_plan.current_period_start = period_start
        organization_plan.current_period_end = period_end
        await self._session.flush()
        await self._session.refresh(organization_plan)
        return organization_plan

    async def schedule_plan_change(
        self,
        organization_plan: OrganizationPlan,
        *,
        pending_plan_definition_id: UUID,
    ) -> OrganizationPlan:
        """Schedule a new plan to take effect at the next renewal boundary."""
        organization_plan.pending_plan_definition_id = pending_plan_definition_id
        await self._session.flush()
        await self._session.refresh(organization_plan)
        return organization_plan

    async def list_due_for_renewal(self, *, as_of: date) -> list[OrganizationPlan]:
        """Return active subscriptions whose current period has already ended."""
        statement: Select[tuple[OrganizationPlan]] = (
            select(OrganizationPlan)
            .options(
                selectinload(OrganizationPlan.plan),
                selectinload(OrganizationPlan.pending_plan),
            )
            .where(
                OrganizationPlan.status == "active",
                OrganizationPlan.current_period_end <= as_of,
            )
            .order_by(OrganizationPlan.current_period_end.asc(), OrganizationPlan.created_at.asc())
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())
