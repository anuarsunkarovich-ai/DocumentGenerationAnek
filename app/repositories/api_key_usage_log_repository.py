"""Repository for API-key request usage logs."""

from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key_usage_log import ApiKeyUsageLog


class ApiKeyUsageLogRepository:
    """Access API-key usage-log records."""

    def __init__(self, session: AsyncSession) -> None:
        """Store the active database session."""
        self._session = session

    async def create(self, usage_log: ApiKeyUsageLog) -> ApiKeyUsageLog:
        """Persist one usage-log entry."""
        self._session.add(usage_log)
        await self._session.flush()
        await self._session.refresh(usage_log)
        return usage_log

    async def list_recent(
        self,
        *,
        organization_id: UUID,
        api_key_id: UUID | None = None,
        limit: int = 50,
    ) -> list[ApiKeyUsageLog]:
        """Return recent usage events for one organization or key."""
        statement: Select[tuple[ApiKeyUsageLog]] = (
            select(ApiKeyUsageLog)
            .where(ApiKeyUsageLog.organization_id == organization_id)
            .order_by(ApiKeyUsageLog.created_at.desc())
            .limit(limit)
        )
        if api_key_id is not None:
            statement = statement.where(ApiKeyUsageLog.api_key_id == api_key_id)
        result = await self._session.execute(statement)
        return list(result.scalars().all())
