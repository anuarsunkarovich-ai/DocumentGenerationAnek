"""Retention cleanup and operational maintenance helpers."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from app.core.config import get_settings
from app.core.database import get_transaction_session
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.document_artifact_repository import DocumentArtifactRepository
from app.repositories.document_repository import DocumentRepository
from app.services.billing_service import BillingService
from app.services.storage import get_storage_service

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MaintenanceCleanupResult:
    """Summary of one maintenance cleanup run."""

    expired_artifacts_deleted: int = 0
    failed_jobs_deleted: int = 0
    audit_logs_deleted: int = 0
    temp_files_deleted: int = 0
    storage_bytes_reclaimed: int = 0


class MaintenanceService:
    """Run retention cleanup for storage, jobs, audit logs, and temp files."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._storage_service = get_storage_service()
        self._billing_service = BillingService()

    async def cleanup(self) -> MaintenanceCleanupResult:
        """Run one full maintenance pass and return its summary."""
        artifact_result = await self._cleanup_expired_artifacts()
        failed_jobs_deleted = await self._cleanup_failed_jobs()
        audit_logs_deleted = await self._cleanup_audit_logs()
        temp_files_deleted = await self._cleanup_temp_files()
        result = MaintenanceCleanupResult(
            expired_artifacts_deleted=artifact_result.expired_artifacts_deleted,
            failed_jobs_deleted=failed_jobs_deleted,
            audit_logs_deleted=audit_logs_deleted,
            temp_files_deleted=temp_files_deleted,
            storage_bytes_reclaimed=artifact_result.storage_bytes_reclaimed,
        )
        logger.info(
            "maintenance cleanup completed",
            extra={
                "event": "maintenance.cleanup_completed",
                "expired_artifacts_deleted": result.expired_artifacts_deleted,
                "failed_jobs_deleted": result.failed_jobs_deleted,
                "audit_logs_deleted": result.audit_logs_deleted,
                "temp_files_deleted": result.temp_files_deleted,
                "storage_bytes_reclaimed": result.storage_bytes_reclaimed,
            },
        )
        return result

    async def _cleanup_expired_artifacts(self) -> MaintenanceCleanupResult:
        cutoff = datetime.now(timezone.utc)
        total_deleted = 0
        total_reclaimed = 0
        batch_size = self._settings.retention.cleanup_batch_size

        while True:
            async with get_transaction_session() as session:
                repository = DocumentArtifactRepository(session)
                artifacts = await repository.list_expired(
                    expired_before=cutoff,
                    limit=batch_size,
                )
                if not artifacts:
                    break

                bytes_by_org: dict[UUID, int] = {}
                for artifact in artifacts:
                    await self._storage_service.delete_object(artifact.storage_key)
                    size_bytes = int(artifact.size_bytes or 0)
                    bytes_by_org[artifact.organization_id] = (
                        bytes_by_org.get(artifact.organization_id, 0) + size_bytes
                    )
                    total_reclaimed += size_bytes

                deleted = await repository.delete_artifacts(artifacts)
                total_deleted += deleted
                for organization_id, bytes_reclaimed in bytes_by_org.items():
                    await self._billing_service.record_storage_usage(
                        organization_id=organization_id,
                        delta_bytes=-bytes_reclaimed,
                        session=session,
                    )
                if deleted < batch_size:
                    break

        return MaintenanceCleanupResult(
            expired_artifacts_deleted=total_deleted,
            storage_bytes_reclaimed=total_reclaimed,
        )

    async def _cleanup_failed_jobs(self) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(
            days=self._settings.retention.failed_job_retention_days
        )
        total_deleted = 0
        batch_size = self._settings.retention.cleanup_batch_size

        while True:
            async with get_transaction_session() as session:
                repository = DocumentRepository(session)
                jobs = await repository.list_failed_before(
                    failed_before=cutoff,
                    limit=batch_size,
                )
                if not jobs:
                    break
                deleted = await repository.delete_jobs(jobs)
                total_deleted += deleted
                if deleted < batch_size:
                    break

        return total_deleted

    async def _cleanup_audit_logs(self) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(
            days=self._settings.retention.audit_log_retention_days
        )
        async with get_transaction_session() as session:
            return await AuditLogRepository(session).delete_older_than(older_than=cutoff)

    async def _cleanup_temp_files(self) -> int:
        temp_dir = self._settings.paths.temp_dir
        if not temp_dir.exists():
            return 0

        cutoff = datetime.now(timezone.utc) - timedelta(
            hours=self._settings.retention.temp_data_retention_hours
        )
        deleted = 0
        for path in sorted(temp_dir.rglob("*"), reverse=True):
            if not path.exists():
                continue
            if path.is_dir():
                self._remove_empty_dir(path)
                continue
            modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            if modified_at >= cutoff:
                continue
            path.unlink(missing_ok=True)
            deleted += 1

        self._remove_empty_dir(temp_dir)
        return deleted

    def _remove_empty_dir(self, path: Path) -> None:
        """Best-effort removal for empty directories produced by temp cleanup."""
        try:
            path.rmdir()
        except OSError:
            return
