"""Admin diagnostics routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.api.controllers.admin_controller import AdminController
from app.api.dependencies.auth import get_current_user
from app.api.dependencies.authorization import require_audit_access
from app.dtos.admin import (
    AdminScopeQuery,
    ApiKeyDisableQuery,
    ApiKeyDisableResponse,
    AuditEventListResponse,
    AuditHistoryQuery,
    CacheInvalidateQuery,
    CacheInvalidationResponse,
    CacheStatsResponse,
    FailedJobsListResponse,
    MaintenanceCleanupResponse,
    ReplayJobQuery,
    ReplayJobResponse,
    UserDisableQuery,
    UserDisableResponse,
    WorkerStatusQuery,
    WorkerStatusResponse,
)
from app.models.user import User
from app.services.operations_service import OperationsService

router = APIRouter()


@router.get("/diagnostics/failed-jobs", response_model=FailedJobsListResponse)
async def list_failed_jobs(
    request: Request,
    query: Annotated[AdminScopeQuery, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
) -> FailedJobsListResponse:
    """Return recent failed jobs for the selected organization."""
    require_audit_access(current_user, query.organization_id, request=request)
    controller = AdminController(service=OperationsService())
    return await controller.list_failed_jobs(
        organization_id=query.organization_id,
        limit=query.limit,
    )


@router.get("/diagnostics/audit-events", response_model=AuditEventListResponse)
async def list_recent_audit_events(
    request: Request,
    query: Annotated[AdminScopeQuery, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AuditEventListResponse:
    """Return recent audit events for the selected organization."""
    require_audit_access(current_user, query.organization_id, request=request)
    controller = AdminController(service=OperationsService())
    return await controller.list_recent_audit_events(
        organization_id=query.organization_id,
        limit=query.limit,
    )


@router.get("/diagnostics/cache-stats", response_model=CacheStatsResponse)
async def get_cache_stats(
    request: Request,
    query: Annotated[WorkerStatusQuery, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
) -> CacheStatsResponse:
    """Return cache usage stats for the selected organization."""
    require_audit_access(current_user, query.organization_id, request=request)
    controller = AdminController(service=OperationsService())
    return await controller.get_cache_stats(organization_id=query.organization_id)


@router.get("/diagnostics/worker-status", response_model=WorkerStatusResponse)
async def get_worker_status(
    request: Request,
    query: Annotated[WorkerStatusQuery, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WorkerStatusResponse:
    """Return worker and queue status."""
    require_audit_access(current_user, query.organization_id, request=request)
    controller = AdminController(service=OperationsService())
    return await controller.get_worker_status(organization_id=query.organization_id)


@router.get("/support/audit-history", response_model=AuditEventListResponse)
async def list_audit_history(
    request: Request,
    query: Annotated[AuditHistoryQuery, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AuditEventListResponse:
    """Return entity-scoped audit history for support operations."""
    require_audit_access(current_user, query.organization_id, request=request)
    controller = AdminController(service=OperationsService())
    return await controller.list_audit_history(
        organization_id=query.organization_id,
        entity_type=query.entity_type,
        entity_id=query.entity_id,
        limit=query.limit,
    )


@router.post("/support/jobs/{job_id}/replay", response_model=ReplayJobResponse)
async def replay_job(
    request: Request,
    job_id: UUID,
    query: Annotated[ReplayJobQuery, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ReplayJobResponse:
    """Replay one document generation job."""
    membership = require_audit_access(current_user, query.organization_id, request=request)
    controller = AdminController(service=OperationsService())
    return await controller.replay_job(
        organization_id=query.organization_id,
        job_id=job_id,
        current_user_id=membership.user_id,
    )


@router.post("/support/jobs/{job_id}/invalidate-cache", response_model=CacheInvalidationResponse)
async def invalidate_cache(
    request: Request,
    job_id: UUID,
    query: Annotated[CacheInvalidateQuery, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
) -> CacheInvalidationResponse:
    """Invalidate cache reuse for one job lineage."""
    membership = require_audit_access(current_user, query.organization_id, request=request)
    controller = AdminController(service=OperationsService())
    return await controller.invalidate_cache(
        organization_id=query.organization_id,
        job_id=job_id,
        current_user_id=membership.user_id,
    )


@router.post("/support/users/{user_id}/disable", response_model=UserDisableResponse)
async def disable_user(
    request: Request,
    user_id: UUID,
    query: Annotated[UserDisableQuery, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserDisableResponse:
    """Disable one user account and revoke active refresh sessions."""
    membership = require_audit_access(current_user, query.organization_id, request=request)
    controller = AdminController(service=OperationsService())
    return await controller.disable_user(
        organization_id=query.organization_id,
        user_id=user_id,
        current_user_id=membership.user_id,
    )


@router.post("/support/api-keys/{api_key_id}/disable", response_model=ApiKeyDisableResponse)
async def disable_api_key(
    request: Request,
    api_key_id: UUID,
    query: Annotated[ApiKeyDisableQuery, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApiKeyDisableResponse:
    """Disable one API key for incident response."""
    membership = require_audit_access(current_user, query.organization_id, request=request)
    controller = AdminController(service=OperationsService())
    return await controller.disable_api_key(
        organization_id=query.organization_id,
        api_key_id=api_key_id,
        current_user_id=membership.user_id,
    )


@router.post("/support/maintenance/cleanup", response_model=MaintenanceCleanupResponse)
async def run_maintenance_cleanup(
    request: Request,
    query: Annotated[WorkerStatusQuery, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MaintenanceCleanupResponse:
    """Trigger one maintenance cleanup pass immediately."""
    require_audit_access(current_user, query.organization_id, request=request)
    controller = AdminController(service=OperationsService())
    return await controller.run_maintenance_cleanup()
