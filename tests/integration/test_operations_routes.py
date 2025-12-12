"""Integration tests for health, metrics, and admin diagnostics routes."""

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
import app.services.operations_service as operations_service_module
from app.dtos.admin import (
    AuditEventListResponse,
    CacheStatsResponse,
    FailedJobsListResponse,
    WorkerStatusResponse,
)
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
