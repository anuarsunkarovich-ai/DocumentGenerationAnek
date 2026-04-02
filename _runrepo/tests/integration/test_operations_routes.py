"""Integration tests for health, admin diagnostics, and support routes."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
import app.services.operations_service as operations_service_module
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
from app.dtos.document import DocumentJobResponse
from app.dtos.health import HealthDependencyResponse, HealthResponse, LiveHealthResponse

pytestmark = pytest.mark.integration


def test_health_routes_return_expected_status_codes(monkeypatch, client: TestClient) -> None:
    """Health routes should distinguish liveness from readiness."""

    async def fake_liveness(self) -> LiveHealthResponse:
        return LiveHealthResponse(status="ok", service="lean-generator-backend")

    async def fake_readiness(self) -> HealthResponse:
        return HealthResponse(
            status="degraded",
            service="lean-generator-backend",
            checks={"redis": HealthDependencyResponse(status="error", detail="unavailable")},
        )

    monkeypatch.setattr(operations_service_module.OperationsService, "get_liveness", fake_liveness)
    monkeypatch.setattr(operations_service_module.OperationsService, "get_readiness", fake_readiness)

    live_response = client.get("/health/live")
    ready_response = client.get("/health/ready")
    summary_response = client.get("/health")

    assert live_response.status_code == 200
    assert live_response.json()["status"] == "ok"
    assert ready_response.status_code == 503
    assert ready_response.json()["status"] == "degraded"
    assert summary_response.status_code == 503
    assert summary_response.headers["X-Request-ID"]
    assert summary_response.headers["X-Correlation-ID"]


def test_metrics_endpoint_returns_prometheus_payload(monkeypatch, client: TestClient) -> None:
    """Metrics endpoint should return Prometheus-formatted output."""

    async def fake_refresh_runtime_metrics(self) -> None:
        return None

    monkeypatch.setattr(
        operations_service_module.OperationsService,
        "refresh_runtime_metrics",
        fake_refresh_runtime_metrics,
    )
    monkeypatch.setattr(main_module, "render_metrics", lambda: (b"custom_metric 1\n", "text/plain"))

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.text == "custom_metric 1\n"


def test_admin_diagnostics_routes_return_service_payloads(
    monkeypatch,
    authenticated_client: TestClient,
    authenticated_membership,
) -> None:
    """Admin diagnostics routes should return operational summaries."""
    organization_id = authenticated_membership.organization_id

    async def fake_failed_jobs(self, *, organization_id, limit):
        assert limit == 25
        return FailedJobsListResponse(items=[])

    async def fake_audit_events(self, *, organization_id, limit):
        assert limit == 25
        return AuditEventListResponse(items=[])

    async def fake_cache_stats(self, *, organization_id):
        return CacheStatsResponse(
            organization_id=organization_id,
            completed_jobs=10,
            cached_jobs=4,
            cached_artifacts=6,
            cache_hit_ratio=0.4,
        )

    async def fake_worker_status(self, *, organization_id):
        return WorkerStatusResponse(
            organization_id=organization_id,
            queue_depth=2,
            workers=[],
        )

    monkeypatch.setattr(operations_service_module.OperationsService, "list_failed_jobs", fake_failed_jobs)
    monkeypatch.setattr(
        operations_service_module.OperationsService,
        "list_recent_audit_events",
        fake_audit_events,
    )
    monkeypatch.setattr(operations_service_module.OperationsService, "get_cache_stats", fake_cache_stats)
    monkeypatch.setattr(
        operations_service_module.OperationsService,
        "get_worker_status",
        fake_worker_status,
    )

    failed_jobs_response = authenticated_client.get(
        "/api/v1/admin/diagnostics/failed-jobs",
        params={"organization_id": str(organization_id)},
    )
    audit_events_response = authenticated_client.get(
        "/api/v1/admin/diagnostics/audit-events",
        params={"organization_id": str(organization_id)},
    )
    cache_stats_response = authenticated_client.get(
        "/api/v1/admin/diagnostics/cache-stats",
        params={"organization_id": str(organization_id)},
    )
    worker_status_response = authenticated_client.get(
        "/api/v1/admin/diagnostics/worker-status",
        params={"organization_id": str(organization_id)},
    )

    assert failed_jobs_response.status_code == 200
    assert failed_jobs_response.json() == {"items": []}
    assert audit_events_response.status_code == 200
    assert audit_events_response.json() == {"items": []}
    assert cache_stats_response.status_code == 200
    assert cache_stats_response.json()["cache_hit_ratio"] == 0.4
    assert worker_status_response.status_code == 200
    assert worker_status_response.json()["queue_depth"] == 2


def test_admin_support_routes_return_service_payloads(
    monkeypatch,
    authenticated_client: TestClient,
    authenticated_membership,
) -> None:
    """Support routes should expose replay, cache, audit, disable, and cleanup operations."""
    organization_id = authenticated_membership.organization_id
    job_id = uuid4()
    user_id = uuid4()
    api_key_id = uuid4()
    issued_at = datetime(2026, 2, 28, 10, 0, tzinfo=timezone.utc)

    async def fake_audit_history(self, *, organization_id, entity_type, entity_id, limit):
        assert entity_type == "document_job"
        assert entity_id == job_id
        assert limit == 50
        return AuditEventListResponse(items=[])

    async def fake_replay_job(self, *, organization_id, job_id, current_user_id):
        assert current_user_id == authenticated_membership.user.id
        return ReplayJobResponse(
            replayed_from_task_id=job_id,
            job=DocumentJobResponse(
                task_id=uuid4(),
                organization_id=organization_id,
                status="queued",
                template_id=uuid4(),
                template_version_id=uuid4(),
                requested_by_user_id=current_user_id,
                from_cache=False,
            ),
        )

    async def fake_invalidate_cache(self, *, organization_id, job_id, current_user_id):
        assert current_user_id == authenticated_membership.user.id
        return CacheInvalidationResponse(
            organization_id=organization_id,
            task_id=job_id,
            cache_key="cache-123",
            invalidated_artifact_count=2,
            invalidated_at=issued_at,
        )

    async def fake_disable_user(self, *, organization_id, user_id, current_user_id):
        assert current_user_id == authenticated_membership.user.id
        return UserDisableResponse(
            id=user_id,
            organization_id=organization_id,
            email="operator@example.com",
            full_name="Operator",
            is_active=False,
            revoked_session_count=3,
        )

    async def fake_disable_api_key(self, *, organization_id, api_key_id, current_user_id):
        assert current_user_id == authenticated_membership.user.id
        return ApiKeyDisableResponse(
            id=api_key_id,
            organization_id=organization_id,
            name="Partner key",
            status="disabled",
            disabled_at=issued_at,
        )

    async def fake_cleanup(self):
        return MaintenanceCleanupResponse(
            expired_artifacts_deleted=4,
            failed_jobs_deleted=1,
            audit_logs_deleted=2,
            temp_files_deleted=3,
            storage_bytes_reclaimed=4096,
        )

    monkeypatch.setattr(
        operations_service_module.OperationsService,
        "list_audit_history",
        fake_audit_history,
    )
    monkeypatch.setattr(operations_service_module.OperationsService, "replay_job", fake_replay_job)
    monkeypatch.setattr(
        operations_service_module.OperationsService,
        "invalidate_cache",
        fake_invalidate_cache,
    )
    monkeypatch.setattr(
        operations_service_module.OperationsService,
        "disable_user",
        fake_disable_user,
    )
    monkeypatch.setattr(
        operations_service_module.OperationsService,
        "disable_api_key",
        fake_disable_api_key,
    )
    monkeypatch.setattr(
        operations_service_module.OperationsService,
        "run_maintenance_cleanup",
        fake_cleanup,
    )

    audit_history_response = authenticated_client.get(
        "/api/v1/admin/support/audit-history",
        params={
            "organization_id": str(organization_id),
            "entity_type": "document_job",
            "entity_id": str(job_id),
        },
    )
    replay_response = authenticated_client.post(
        f"/api/v1/admin/support/jobs/{job_id}/replay",
        params={"organization_id": str(organization_id)},
    )
    invalidate_response = authenticated_client.post(
        f"/api/v1/admin/support/jobs/{job_id}/invalidate-cache",
        params={"organization_id": str(organization_id)},
    )
    disable_user_response = authenticated_client.post(
        f"/api/v1/admin/support/users/{user_id}/disable",
        params={"organization_id": str(organization_id)},
    )
    disable_api_key_response = authenticated_client.post(
        f"/api/v1/admin/support/api-keys/{api_key_id}/disable",
        params={"organization_id": str(organization_id)},
    )
    cleanup_response = authenticated_client.post(
        "/api/v1/admin/support/maintenance/cleanup",
        params={"organization_id": str(organization_id)},
    )

    assert audit_history_response.status_code == 200
    assert audit_history_response.json() == {"items": []}
    assert replay_response.status_code == 200
    assert replay_response.json()["replayed_from_task_id"] == str(job_id)
    assert invalidate_response.status_code == 200
    assert invalidate_response.json()["invalidated_artifact_count"] == 2
    assert disable_user_response.status_code == 200
    assert disable_user_response.json()["revoked_session_count"] == 3
    assert disable_api_key_response.status_code == 200
    assert disable_api_key_response.json()["status"] == "disabled"
    assert cleanup_response.status_code == 200
    assert cleanup_response.json()["storage_bytes_reclaimed"] == 4096
