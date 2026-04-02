"""Audit logging helpers for operational traceability."""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.request_context import get_correlation_id, get_request_id
from app.models.audit_log import AuditLog
from app.models.enums import AuditAction
from app.repositories.audit_log_repository import AuditLogRepository


class AuditService:
    """Persist immutable audit log events for tenant-scoped actions."""

    def __init__(self, session: AsyncSession) -> None:
        """Store the repository dependency."""
        self._repository = AuditLogRepository(session)

    async def log_event(
        self,
        *,
        organization_id: UUID,
        user_id: UUID | None,
        action: AuditAction,
        entity_type: str,
        entity_id: UUID | None,
        payload: dict[str, Any],
    ) -> AuditLog:
        """Persist one audit event."""
        trace: dict[str, str] = {}
        request_id = get_request_id()
        correlation_id = get_correlation_id()
        if request_id is not None:
            trace["request_id"] = request_id
        if correlation_id is not None:
            trace["correlation_id"] = correlation_id
        payload_with_trace = dict(payload)
        if trace:
            payload_with_trace["trace"] = trace
        return await self._repository.create(
            AuditLog(
                organization_id=organization_id,
                user_id=user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                payload=payload_with_trace,
            )
        )
