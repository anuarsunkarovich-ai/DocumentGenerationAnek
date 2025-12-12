"""Operational diagnostics and infrastructure status helpers."""

import asyncio
from typing import cast

from redis import Redis
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import get_transaction_session
from app.core.metrics import observe_queue_depth, observe_worker_status
from app.dtos.admin import (
    AuditEventDiagnosticResponse,
    AuditEventListResponse,
    CacheStatsResponse,
    FailedJobDiagnosticResponse,
    FailedJobsListResponse,
    WorkerNodeStatusResponse,
    WorkerStatusResponse,
)
from app.dtos.health import HealthDependencyResponse, HealthResponse, LiveHealthResponse
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.document_repository import DocumentRepository
from app.services.storage import get_storage_service


class OperationsService:
    """Expose runtime health and admin diagnostics."""

    def __init__(self) -> None:
        self._settings = get_settings()

    async def get_liveness(self) -> LiveHealthResponse:
        """Return a process-only liveness response."""
        return LiveHealthResponse(status="ok", service="lean-generator-backend")

    async def get_readiness(self) -> HealthResponse:
        """Return dependency readiness for database, storage, and Redis."""
        checks: dict[str, HealthDependencyResponse] = {}

        try:
            async with get_transaction_session() as session:
                await session.execute(text("SELECT 1"))
            checks["database"] = HealthDependencyResponse(status="ok")
        except Exception as error:
            checks["database"] = HealthDependencyResponse(status="error", detail=str(error))

        try:
            await get_storage_service().ensure_bucket()
            checks["storage"] = HealthDependencyResponse(status="ok")
        except Exception as error:
            checks["storage"] = HealthDependencyResponse(status="error", detail=str(error))

        try:
            await asyncio.to_thread(self._get_redis_client().ping)
            checks["redis"] = HealthDependencyResponse(status="ok")
        except Exception as error:
            checks["redis"] = HealthDependencyResponse(status="error", detail=str(error))

        overall_status = (
            "ok" if all(item.status == "ok" for item in checks.values()) else "degraded"
        )
        return HealthResponse(
            status=overall_status,
            service="lean-generator-backend",
            checks=checks,
        )

    async def list_failed_jobs(
        self,
        *,
        organization_id,
        limit: int,
    ) -> FailedJobsListResponse:
        """Return recent failed jobs for one organization."""
        async with get_transaction_session() as session:
            jobs = await DocumentRepository(session).list_failed_jobs(
                organization_id=organization_id,
                limit=limit,
            )
            return FailedJobsListResponse(
                items=[
                    FailedJobDiagnosticResponse(
                        task_id=job.id,
                        organization_id=job.organization_id,
                        template_id=job.template_id,
                        template_version_id=job.template_version_id,
                        requested_by_user_id=job.requested_by_user_id,
                        status=job.status.value,
                        error_message=job.error_message,
                        created_at=job.created_at,
                        completed_at=job.completed_at,
                    )
                    for job in jobs
                ]
            )

    async def list_recent_audit_events(
        self,
        *,
        organization_id,
        limit: int,
    ) -> AuditEventListResponse:
        """Return recent audit events for one organization."""
        async with get_transaction_session() as session:
            events = await AuditLogRepository(session).list_recent(
                organization_id=organization_id,
                limit=limit,
            )
            return AuditEventListResponse(
                items=[
                    AuditEventDiagnosticResponse(
                        id=event.id,
                        organization_id=event.organization_id,
                        user_id=event.user_id,
                        action=event.action.value,
                        entity_type=event.entity_type,
                        entity_id=event.entity_id,
                        payload=event.payload,
                        created_at=event.created_at,
                    )
                    for event in events
                ]
            )

    async def get_cache_stats(self, *, organization_id) -> CacheStatsResponse:
        """Return aggregate cache stats for one organization."""
        async with get_transaction_session() as session:
            stats = await DocumentRepository(session).get_cache_stats(organization_id=organization_id)

        completed_jobs = stats["completed_jobs"]
        cached_jobs = stats["cached_jobs"]
        cache_hit_ratio = (cached_jobs / completed_jobs) if completed_jobs else 0.0
        return CacheStatsResponse(
            organization_id=organization_id,
            completed_jobs=completed_jobs,
            cached_jobs=cached_jobs,
            cached_artifacts=stats["cached_artifacts"],
            cache_hit_ratio=round(cache_hit_ratio, 4),
        )

    async def get_worker_status(self, *, organization_id) -> WorkerStatusResponse:
        """Return queue depth and worker availability."""
        queue_depth, worker_map = await self._get_runtime_status()

        return WorkerStatusResponse(
            organization_id=organization_id,
            queue_depth=queue_depth,
            workers=[
                WorkerNodeStatusResponse(name=name, is_online=is_online)
                for name, is_online in sorted(worker_map.items())
            ],
        )

    async def refresh_runtime_metrics(self) -> None:
        """Refresh queue-depth and worker gauges before metrics export."""
        try:
            await self._get_runtime_status()
        except Exception:
            return

    def _get_redis_client(self) -> Redis:
        """Build a Redis client from configured broker settings."""
        return Redis.from_url(self._settings.redis.broker_url, decode_responses=True)

    def _get_queue_depth(self) -> int:
        """Return the current document-generation queue depth."""
        client = self._get_redis_client()
        return cast(int, client.llen(self._settings.worker.queue_name))

    async def _get_runtime_status(self) -> tuple[int, dict[str, bool]]:
        """Return queue depth and worker availability, updating gauges on the way."""
        from app.workers.celery_app import celery_app

        queue_depth = await asyncio.to_thread(self._get_queue_depth)
        inspect = celery_app.control.inspect(timeout=1)
        pings = await asyncio.to_thread(inspect.ping)
        worker_map = {name: True for name in (pings or {}).keys()}
        observe_queue_depth(depth=queue_depth)
        observe_worker_status(workers=worker_map)
        return queue_depth, worker_map
