"""Repository for audit log persistence."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


class AuditLogRepository:
    """Access immutable audit log records."""

    def __init__(self, session: AsyncSession) -> None:
        """Store the active database session."""
        self._session = session

    async def create(self, audit_log: AuditLog) -> AuditLog:
        """Persist an audit log entry."""
        self._session.add(audit_log)
        await self._session.flush()
        await self._session.refresh(audit_log)
        return audit_log

    async def list_for_entity(
        self,
        *,
        organization_id: UUID,
        entity_type: str,
        entity_id: UUID,
    ) -> list[AuditLog]:
        """Return all audit log entries for one entity inside one organization."""
        statement: Select[tuple[AuditLog]] = (
            select(AuditLog)
            .where(
                AuditLog.organization_id == organization_id,
                AuditLog.entity_type == entity_type,
                AuditLog.entity_id == entity_id,
            )
            .order_by(AuditLog.created_at.desc())
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def list_recent(
        self,
        *,
        organization_id: UUID,
        limit: int,
        created_after: datetime | None = None,
    ) -> list[AuditLog]:
        """Return recent audit log entries for one organization."""
        statement: Select[tuple[AuditLog]] = (
            select(AuditLog)
            .where(AuditLog.organization_id == organization_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        if created_after is not None:
            statement = statement.where(AuditLog.created_at >= created_after)
        result = await self._session.execute(statement)
        return list(result.scalars().all())
