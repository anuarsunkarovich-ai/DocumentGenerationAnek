"""Operational diagnostics and infrastructure status helpers."""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import cast

from fastapi import BackgroundTasks
from redis import Redis
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import get_transaction_session
from app.core.exceptions import ConflictError, NotFoundError
from app.core.metrics import observe_queue_depth, observe_worker_status
from app.dtos.admin import (
    ApiKeyDisableResponse,
    AuditEventDiagnosticResponse,
    AuditEventListResponse,
    CacheInvalidationResponse,
    CacheStatsResponse,
    FailedJobDiagnosticResponse,
    FailedJobsListResponse,
    MaintenanceCleanupResponse,
    ReplayJobResponse,
    UserDisableResponse,
    WorkerNodeStatusResponse,
    WorkerStatusResponse,
)
from app.dtos.document import DocumentJobCreateRequest
from app.dtos.health import HealthDependencyResponse, HealthResponse, LiveHealthResponse
from app.models.enums import AuditAction
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.auth_session_repository import AuthSessionRepository
from app.repositories.document_artifact_repository import DocumentArtifactRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.user_repository import UserRepository
from app.services.api_key_service import ApiKeyService
from app.services.audit_service import AuditService
from app.services.billing_service import BillingService
from app.services.document_service import DocumentService
from app.services.maintenance_service import MaintenanceService
from app.services.storage import get_storage_service


class OperationsService:
    """Expose runtime health and admin diagnostics."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._billing_service = BillingService()

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
            retention_days = await self._billing_service.get_audit_retention_days(
                organization_id=organization_id,
                session=session,
            )
            events = await AuditLogRepository(session).list_recent(
                organization_id=organization_id,
                limit=limit,
                created_after=datetime.now(timezone.utc) - timedelta(days=retention_days),
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

    async def list_audit_history(
        self,
        *,
        organization_id,
        entity_type: str,
        entity_id,
        limit: int,
    ) -> AuditEventListResponse:
        """Return retained audit history for one entity in one organization."""
        async with get_transaction_session() as session:
            retention_days = await self._billing_service.get_audit_retention_days(
                organization_id=organization_id,
                session=session,
            )
            created_after = datetime.now(timezone.utc) - timedelta(days=retention_days)
            events = await AuditLogRepository(session).list_for_entity(
                organization_id=organization_id,
                entity_type=entity_type,
                entity_id=entity_id,
                limit=limit,
                created_after=created_after,
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

    async def replay_job(
        self,
        *,
        organization_id,
        job_id,
        current_user_id,
    ) -> ReplayJobResponse:
        """Clone one existing job request back into the generation queue."""
        async with get_transaction_session() as session:
            source_job = await DocumentRepository(session).get_by_id(
                job_id,
                organization_id=organization_id,
            )
            if source_job is None:
                raise NotFoundError("Document job was not found.")
            payload = DocumentJobCreateRequest.model_validate(source_job.input_payload)

        job_response = await DocumentService().create_job(
            payload,
            BackgroundTasks(),
            current_user_id=current_user_id,
        )

        async with get_transaction_session() as session:
            await AuditService(session).log_event(
                organization_id=organization_id,
                user_id=current_user_id,
                action=AuditAction.DOCUMENT_JOB_REPLAYED,
                entity_type="document_job",
                entity_id=job_response.task_id,
                payload={
                    "replayed_from_task_id": str(job_id),
                    "template_id": str(job_response.template_id) if job_response.template_id else None,
                    "template_version_id": (
                        str(job_response.template_version_id)
                        if job_response.template_version_id
                        else None
                    ),
                },
            )

        return ReplayJobResponse(
            replayed_from_task_id=job_id,
            job=job_response,
        )

    async def invalidate_cache(
        self,
        *,
        organization_id,
        job_id,
        current_user_id,
    ) -> CacheInvalidationResponse:
        """Expire cache lineage for one generated job so it cannot be reused."""
        invalidated_at = datetime.now(timezone.utc)
        async with get_transaction_session() as session:
            job = await DocumentRepository(session).get_by_id(
                job_id,
                organization_id=organization_id,
            )
            if job is None:
                raise NotFoundError("Document job was not found.")

            invalidated_artifacts = []
            if job.cache_key:
                invalidated_artifacts = await DocumentArtifactRepository(session).expire_for_cache_key(
                    organization_id=organization_id,
                    template_version_id=job.template_version_id,
                    cache_key=job.cache_key,
                    expires_at=invalidated_at,
                )
            await AuditService(session).log_event(
                organization_id=organization_id,
                user_id=current_user_id,
                action=AuditAction.CACHE_INVALIDATED,
                entity_type="document_job",
                entity_id=job.id,
                payload={
                    "cache_key": job.cache_key,
                    "invalidated_artifact_count": len(invalidated_artifacts),
                },
            )

            return CacheInvalidationResponse(
                organization_id=organization_id,
                task_id=job.id,
                cache_key=job.cache_key,
                invalidated_artifact_count=len(invalidated_artifacts),
                invalidated_at=invalidated_at,
            )

    async def disable_user(
        self,
        *,
        organization_id,
        user_id,
        current_user_id,
    ) -> UserDisableResponse:
        """Disable one user account and revoke its refresh sessions."""
        if user_id == current_user_id:
            raise ConflictError("Admins cannot disable their own account.")

        async with get_transaction_session() as session:
            user_repository = UserRepository(session)
            session_repository = AuthSessionRepository(session)
            audit_service = AuditService(session)
            user = await user_repository.get_by_id(user_id)
            if user is None or not any(
                membership.organization_id == organization_id for membership in user.memberships
            ):
                raise NotFoundError("User was not found.")

            user = await user_repository.set_active(user, is_active=False)
            revoked_session_count = await session_repository.revoke_all_for_user(user_id=user.id)
            await audit_service.log_event(
                organization_id=organization_id,
                user_id=current_user_id,
                action=AuditAction.USER_DISABLED,
                entity_type="user",
                entity_id=user.id,
                payload={
                    "email": user.email,
                    "revoked_session_count": revoked_session_count,
                },
            )
            return UserDisableResponse(
                id=user.id,
                organization_id=organization_id,
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
                revoked_session_count=revoked_session_count,
            )

    async def disable_api_key(
        self,
        *,
        organization_id,
        api_key_id,
        current_user_id,
    ) -> ApiKeyDisableResponse:
        """Disable one API key for support and incident response workflows."""
        disabled_at = datetime.now(timezone.utc)
        api_key = await ApiKeyService().disable_api_key(
            organization_id=organization_id,
            api_key_id=api_key_id,
            current_user_id=current_user_id,
        )
        return ApiKeyDisableResponse(
            id=api_key.id,
            organization_id=api_key.organization_id,
            name=api_key.name,
            status=api_key.status,
            disabled_at=disabled_at,
        )

    async def run_maintenance_cleanup(self) -> MaintenanceCleanupResponse:
        """Run one cleanup pass immediately and return the summary."""
        result = await MaintenanceService().cleanup()
        return MaintenanceCleanupResponse(
            expired_artifacts_deleted=result.expired_artifacts_deleted,
            failed_jobs_deleted=result.failed_jobs_deleted,
            audit_logs_deleted=result.audit_logs_deleted,
            temp_files_deleted=result.temp_files_deleted,
            storage_bytes_reclaimed=result.storage_bytes_reclaimed,
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
