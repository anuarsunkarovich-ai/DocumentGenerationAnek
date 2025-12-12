"""DTOs for admin diagnostics and operations endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.dtos.common import BaseDTO


class AdminScopeQuery(BaseDTO):
    """Common tenant scope query for admin diagnostics."""

    organization_id: UUID
    limit: int = Field(default=25, ge=1, le=100)


class WorkerStatusQuery(BaseDTO):
    """Tenant-scoped query for worker status checks."""

    organization_id: UUID


class FailedJobDiagnosticResponse(BaseDTO):
    """Summarized failed job response for admins."""

    task_id: UUID
    organization_id: UUID
    template_id: UUID
    template_version_id: UUID
    requested_by_user_id: UUID | None = None
    status: str
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class FailedJobsListResponse(BaseDTO):
    """List of recent failed jobs."""

    items: list[FailedJobDiagnosticResponse] = Field(default_factory=list)


class AuditEventDiagnosticResponse(BaseDTO):
    """Summarized audit event for diagnostics."""

    id: UUID
    organization_id: UUID
    user_id: UUID | None = None
    action: str
    entity_type: str
    entity_id: UUID | None = None
    payload: dict = Field(default_factory=dict)
    created_at: datetime


class AuditEventListResponse(BaseDTO):
    """List of recent audit events."""

    items: list[AuditEventDiagnosticResponse] = Field(default_factory=list)


class CacheStatsResponse(BaseDTO):
    """Cache usage summary for one organization."""

    organization_id: UUID
    completed_jobs: int
    cached_jobs: int
    cached_artifacts: int
    cache_hit_ratio: float


class WorkerNodeStatusResponse(BaseDTO):
    """Status for one worker node."""

    name: str
    is_online: bool


class WorkerStatusResponse(BaseDTO):
    """Worker and queue status summary."""

    organization_id: UUID
    queue_depth: int
    workers: list[WorkerNodeStatusResponse] = Field(default_factory=list)
