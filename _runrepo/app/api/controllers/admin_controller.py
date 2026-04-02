"""Controller helpers for admin diagnostics endpoints."""

from uuid import UUID

from app.dtos.admin import (
    ApiKeyDisableResponse,
    AuditEventListResponse,
    CacheInvalidationResponse,
    CacheStatsResponse,
    FailedJobsListResponse,
    MaintenanceCleanupResponse,
    ReplayJobResponse,
    UserDisableResponse,
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

    async def list_audit_history(
        self,
        *,
        organization_id: UUID,
        entity_type: str,
        entity_id: UUID,
        limit: int,
    ) -> AuditEventListResponse:
        """Return audit history for one entity."""
        return await self._service.list_audit_history(
            organization_id=organization_id,
            entity_type=entity_type,
            entity_id=entity_id,
            limit=limit,
        )

    async def replay_job(
        self,
        *,
        organization_id: UUID,
        job_id: UUID,
        current_user_id: UUID,
    ) -> ReplayJobResponse:
        """Replay one document generation job."""
        return await self._service.replay_job(
            organization_id=organization_id,
            job_id=job_id,
            current_user_id=current_user_id,
        )

    async def invalidate_cache(
        self,
        *,
        organization_id: UUID,
        job_id: UUID,
        current_user_id: UUID,
    ) -> CacheInvalidationResponse:
        """Invalidate one cache lineage."""
        return await self._service.invalidate_cache(
            organization_id=organization_id,
            job_id=job_id,
            current_user_id=current_user_id,
        )

    async def disable_user(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        current_user_id: UUID,
    ) -> UserDisableResponse:
        """Disable one user account."""
        return await self._service.disable_user(
            organization_id=organization_id,
            user_id=user_id,
            current_user_id=current_user_id,
        )

    async def disable_api_key(
        self,
        *,
        organization_id: UUID,
        api_key_id: UUID,
        current_user_id: UUID,
    ) -> ApiKeyDisableResponse:
        """Disable one API key."""
        return await self._service.disable_api_key(
            organization_id=organization_id,
            api_key_id=api_key_id,
            current_user_id=current_user_id,
        )

    async def run_maintenance_cleanup(self) -> MaintenanceCleanupResponse:
        """Run one maintenance cleanup pass."""
        return await self._service.run_maintenance_cleanup()
