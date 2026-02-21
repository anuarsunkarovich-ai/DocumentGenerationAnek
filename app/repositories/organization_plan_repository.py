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
            .options(selectinload(OrganizationPlan.plan))
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
    ) -> OrganizationPlan:
        """Roll one organization into a new billing period."""
        organization_plan.current_period_start = period_start
        organization_plan.current_period_end = period_end
        await self._session.flush()
        await self._session.refresh(organization_plan)
        return organization_plan
