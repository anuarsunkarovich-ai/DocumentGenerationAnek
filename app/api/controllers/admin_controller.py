"""Controller helpers for admin diagnostics endpoints."""

from uuid import UUID

from app.dtos.admin import (
    AuditEventListResponse,
    CacheStatsResponse,
    FailedJobsListResponse,
    WorkerStatusResponse,
)
from app.services.operations_service import OperationsService


class AdminController:
    """Coordinate admin diagnostics requests."""

    def __init__(self, service: OperationsService) -> None:
        self._service = service

    async def list_failed_jobs(
        self,
        *,
        organization_id: UUID,
        limit: int,
    ) -> FailedJobsListResponse:
        """Return recent failed jobs for one tenant."""
        return await self._service.list_failed_jobs(
            organization_id=organization_id,
            limit=limit,
        )

    async def list_recent_audit_events(
        self,
        *,
        organization_id: UUID,
        limit: int,
    ) -> AuditEventListResponse:
        """Return recent audit events for one tenant."""
        return await self._service.list_recent_audit_events(
            organization_id=organization_id,
            limit=limit,
        )

    async def get_cache_stats(self, *, organization_id: UUID) -> CacheStatsResponse:
        """Return cache usage stats for one tenant."""
        return await self._service.get_cache_stats(organization_id=organization_id)

    async def get_worker_status(self, *, organization_id: UUID) -> WorkerStatusResponse:
        """Return worker availability for diagnostics."""
        return await self._service.get_worker_status(organization_id=organization_id)
