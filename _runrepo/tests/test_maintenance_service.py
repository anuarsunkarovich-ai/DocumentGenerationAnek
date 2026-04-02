"""Tests for retention cleanup and operational maintenance helpers."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

import app.services.maintenance_service as maintenance_module
from app.core.config import AppSettings, PathsSettings, RetentionSettings, Settings
from app.services.maintenance_service import MaintenanceService


@pytest.mark.anyio
async def test_maintenance_cleanup_deletes_expired_artifacts_jobs_audits_and_temp_files(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Maintenance cleanup should remove expired retained data and temp files."""
    organization_id = uuid4()
    storage_key = "artifacts/org/job/output.pdf"
    expired_artifact = SimpleNamespace(
        id=uuid4(),
        organization_id=organization_id,
        size_bytes=1024,
        storage_key=storage_key,
    )
    expired_job = SimpleNamespace(id=uuid4())
    deleted_storage_keys: list[str] = []
    storage_adjustments: list[tuple[object, int]] = []
    state = {"artifacts_returned": False, "jobs_returned": False}

    temp_dir = tmp_path / "tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    stale_file = temp_dir / "stale.tmp"
    stale_file.write_text("stale", encoding="utf-8")
    stale_timestamp = (datetime.now() - timedelta(hours=2)).timestamp()
    os.utime(stale_file, (stale_timestamp, stale_timestamp))

    settings = Settings(
        app=AppSettings(environment="development"),
        paths=PathsSettings(temp_dir=temp_dir),
        retention=RetentionSettings(
            generated_artifact_retention_days=30,
            failed_job_retention_days=14,
            audit_log_retention_days=90,
            temp_data_retention_hours=0,
            cleanup_batch_size=50,
        ),
    )

    @asynccontextmanager
    async def fake_transaction_session():
        yield object()

    class FakeArtifactRepository:
        def __init__(self, session: object) -> None:
            _ = session

        async def list_expired(self, *, expired_before, limit):
            _ = expired_before, limit
            if state["artifacts_returned"]:
                return []
            state["artifacts_returned"] = True
            return [expired_artifact]

        async def delete_artifacts(self, artifacts):
            assert artifacts == [expired_artifact]
            return len(artifacts)

    class FakeDocumentRepository:
        def __init__(self, session: object) -> None:
            _ = session

        async def list_failed_before(self, *, failed_before, limit):
            _ = failed_before, limit
            if state["jobs_returned"]:
                return []
            state["jobs_returned"] = True
            return [expired_job]

        async def delete_jobs(self, jobs):
            assert jobs == [expired_job]
            return len(jobs)

    class FakeAuditLogRepository:
        def __init__(self, session: object) -> None:
            _ = session

        async def delete_older_than(self, *, older_than):
            _ = older_than
            return 2

    class FakeStorageService:
        async def delete_object(self, key: str) -> None:
            deleted_storage_keys.append(key)

    class FakeBillingService:
        async def record_storage_usage(self, *, organization_id, delta_bytes, session):
            _ = session
            storage_adjustments.append((organization_id, delta_bytes))

    monkeypatch.setattr(maintenance_module, "get_settings", lambda: settings)
    monkeypatch.setattr(maintenance_module, "get_transaction_session", fake_transaction_session)
    monkeypatch.setattr(maintenance_module, "DocumentArtifactRepository", FakeArtifactRepository)
    monkeypatch.setattr(maintenance_module, "DocumentRepository", FakeDocumentRepository)
    monkeypatch.setattr(maintenance_module, "AuditLogRepository", FakeAuditLogRepository)
    monkeypatch.setattr(maintenance_module, "get_storage_service", lambda: FakeStorageService())
    monkeypatch.setattr(maintenance_module, "BillingService", FakeBillingService)

    result = await MaintenanceService().cleanup()

    assert result.expired_artifacts_deleted == 1
    assert result.failed_jobs_deleted == 1
    assert result.audit_logs_deleted == 2
    assert result.temp_files_deleted == 1
    assert result.storage_bytes_reclaimed == 1024
    assert deleted_storage_keys == [storage_key]
    assert storage_adjustments == [(organization_id, -1024)]
    assert not stale_file.exists()
