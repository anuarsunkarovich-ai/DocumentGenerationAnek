"""Repository for monthly organization usage meters."""

from datetime import date
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization_usage_meter import OrganizationUsageMeter


class OrganizationUsageMeterRepository:
    """Access monthly usage meters."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_period(
        self,
        *,
        organization_id: UUID,
        period_start: date,
    ) -> OrganizationUsageMeter | None:
        """Return the usage meter for one org-month."""
        statement: Select[tuple[OrganizationUsageMeter]] = select(OrganizationUsageMeter).where(
            OrganizationUsageMeter.organization_id == organization_id,
            OrganizationUsageMeter.period_start == period_start,
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def create(self, usage_meter: OrganizationUsageMeter) -> OrganizationUsageMeter:
        """Persist one usage meter."""
        self._session.add(usage_meter)
        await self._session.flush()
        await self._session.refresh(usage_meter)
        return usage_meter

    async def increment_generation(self, usage_meter: OrganizationUsageMeter, amount: int = 1) -> None:
        """Increment accepted generation requests."""
        usage_meter.generation_count += amount
        await self._session.flush()

    async def adjust_storage_bytes(
        self,
        usage_meter: OrganizationUsageMeter,
        *,
        delta_bytes: int,
    ) -> None:
        """Adjust stored byte totals."""
        usage_meter.storage_bytes = max(0, usage_meter.storage_bytes + delta_bytes)
        await self._session.flush()

    async def set_template_count(
        self,
        usage_meter: OrganizationUsageMeter,
        *,
        template_count: int,
    ) -> None:
        """Sync the tracked template count."""
        usage_meter.template_count = max(0, template_count)
        await self._session.flush()

    async def set_user_count(
        self,
        usage_meter: OrganizationUsageMeter,
        *,
        user_count: int,
    ) -> None:
        """Sync the tracked user count."""
        usage_meter.user_count = max(0, user_count)
        await self._session.flush()

    async def increment_premium_feature(
        self,
        usage_meter: OrganizationUsageMeter,
        *,
        feature_key: str,
        amount: int = 1,
    ) -> None:
        """Increment one premium feature counter inside the JSON payload."""
        premium_feature_usage = dict(usage_meter.premium_feature_usage or {})
        premium_feature_usage[feature_key] = int(premium_feature_usage.get(feature_key, 0)) + amount
        usage_meter.premium_feature_usage = premium_feature_usage
        await self._session.flush()
