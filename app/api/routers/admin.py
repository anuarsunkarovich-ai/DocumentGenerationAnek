"""Admin diagnostics routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.controllers.admin_controller import AdminController
from app.api.dependencies.auth import get_current_user
from app.api.dependencies.authorization import require_audit_access
from app.dtos.admin import (
    AdminScopeQuery,
    AuditEventListResponse,
    CacheStatsResponse,
    FailedJobsListResponse,
    WorkerStatusQuery,
    WorkerStatusResponse,
)
from app.models.user import User
from app.services.operations_service import OperationsService

router = APIRouter(prefix="/diagnostics")


@router.get("/failed-jobs", response_model=FailedJobsListResponse)
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


@router.get("/audit-events", response_model=AuditEventListResponse)
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


@router.get("/cache-stats", response_model=CacheStatsResponse)
async def get_cache_stats(
    request: Request,
    query: Annotated[WorkerStatusQuery, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
) -> CacheStatsResponse:
    """Return cache usage stats for the selected organization."""
    require_audit_access(current_user, query.organization_id, request=request)
    controller = AdminController(service=OperationsService())
    return await controller.get_cache_stats(organization_id=query.organization_id)


@router.get("/worker-status", response_model=WorkerStatusResponse)
async def get_worker_status(
    request: Request,
    query: Annotated[WorkerStatusQuery, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WorkerStatusResponse:
    """Return worker and queue status."""
    require_audit_access(current_user, query.organization_id, request=request)
    controller = AdminController(service=OperationsService())
    return await controller.get_worker_status(organization_id=query.organization_id)
