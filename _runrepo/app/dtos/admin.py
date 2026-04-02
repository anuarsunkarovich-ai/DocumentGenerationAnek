"""DTOs for admin diagnostics and operations endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.dtos.common import BaseDTO
from app.dtos.document import DocumentJobResponse


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


class AuditHistoryQuery(BaseDTO):
    """Entity-scoped audit lookup query for support tooling."""

    organization_id: UUID
    entity_type: str = Field(min_length=1, max_length=100)
    entity_id: UUID
    limit: int = Field(default=50, ge=1, le=200)


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


class ReplayJobQuery(BaseDTO):
    """Tenant-scoped query for replaying one document job."""

    organization_id: UUID


class ReplayJobResponse(BaseDTO):
    """Response for a replayed generation job."""

    replayed_from_task_id: UUID
    job: DocumentJobResponse


class CacheInvalidateQuery(BaseDTO):
    """Tenant-scoped query for invalidating one cache lineage."""

    organization_id: UUID


class CacheInvalidationResponse(BaseDTO):
    """Response describing one cache invalidation operation."""

    organization_id: UUID
    task_id: UUID
    cache_key: str | None = None
    invalidated_artifact_count: int
    invalidated_at: datetime


class UserDisableQuery(BaseDTO):
    """Tenant-scoped query for disabling one user."""

    organization_id: UUID


class UserDisableResponse(BaseDTO):
    """Response for user disable operations."""

    id: UUID
    organization_id: UUID
    email: str
    full_name: str | None = None
    is_active: bool
    revoked_session_count: int


class ApiKeyDisableQuery(BaseDTO):
    """Tenant-scoped query for disabling one API key."""

    organization_id: UUID


class ApiKeyDisableResponse(BaseDTO):
    """Response for API-key disable operations."""

    id: UUID
    organization_id: UUID
    name: str
    status: str
    disabled_at: datetime


class MaintenanceCleanupResponse(BaseDTO):
    """Summary of one manual or scheduled cleanup pass."""

    expired_artifacts_deleted: int
    failed_jobs_deleted: int
    audit_logs_deleted: int
    temp_files_deleted: int
    storage_bytes_reclaimed: int
