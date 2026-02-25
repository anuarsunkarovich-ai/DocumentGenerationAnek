"""Integration tests for public machine-auth API routes."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import BackgroundTasks
from fastapi.testclient import TestClient

import app.services.api_key_service as api_key_service_module
import app.services.document_service as document_service_module
import app.services.operations_service as operations_service_module
import app.services.template_service as template_service_module
from app.core.exceptions import TooManyRequestsError
from app.dtos.admin import AuditEventDiagnosticResponse, AuditEventListResponse
from app.dtos.api_key import ApiKeyScope
from app.dtos.document import (
    DocumentJobCreateRequest,
    DocumentJobResponse,
    DocumentJobStatusResponse,
    DocumentVerificationArtifactResponse,
    DocumentVerificationResponse,
)
from app.dtos.template import TemplateListResponse, TemplateResponse
from app.services.api_key_service import ApiKeyPrincipal

pytestmark = pytest.mark.integration


def build_principal(
    *,
    scopes: tuple[str, ...],
    required_scope: str,
    organization_id=None,
    api_key_id=None,
) -> ApiKeyPrincipal:
    """Build a fake API-key principal for public route tests."""
    return ApiKeyPrincipal(
        api_key_id=api_key_id or uuid4(),
        organization_id=organization_id or uuid4(),
        scopes=scopes,
        key_prefix="lgk_public",
        scope=required_scope,
    )


def test_public_templates_require_api_key(client: TestClient) -> None:
    """Public machine routes should reject requests with no API key header."""
    response = client.get("/api/v1/public/templates")

    assert response.status_code == 401
    assert response.json()["detail"] == "API key was not provided."


def test_public_templates_use_key_tenant_and_log_usage(
    monkeypatch,
    client: TestClient,
) -> None:
    """Template reads should derive tenant context from the API key and emit usage logs."""
    principal = build_principal(
        scopes=(ApiKeyScope.TEMPLATES_READ,),
        required_scope=ApiKeyScope.TEMPLATES_READ,
    )
    usage_log: dict[str, object] = {}

    async def fake_resolve_api_key_principal(self, *, raw_key, required_scope):
        assert raw_key == "public-test-key"
        assert required_scope == ApiKeyScope.TEMPLATES_READ
        return build_principal(
            scopes=(ApiKeyScope.TEMPLATES_READ,),
            required_scope=required_scope,
            organization_id=principal.organization_id,
            api_key_id=principal.api_key_id,
        )

    async def fake_enforce_limits(self, api_principal):
        assert api_principal.organization_id == principal.organization_id
        return None

    async def fake_log_usage(
        self,
        *,
        principal,
        method,
        path,
        status_code,
        rate_limited,
        request_id=None,
        correlation_id=None,
    ):
        usage_log.update(
            {
                "api_key_id": principal.api_key_id,
                "method": method,
                "path": path,
                "status_code": status_code,
                "rate_limited": rate_limited,
                "request_id": request_id,
                "correlation_id": correlation_id,
            }
        )

    async def fake_list_templates(self, organization_id, *, published_only=False):
        assert organization_id == principal.organization_id
        assert published_only is True
        return TemplateListResponse(
            items=[
                TemplateResponse(
                    id=uuid4(),
                    organization_id=organization_id,
                    name="Published certificate",
                    code="published-certificate",
                    status="active",
                    description=None,
                    current_version=None,
                )
            ]
        )

    monkeypatch.setattr(
        api_key_service_module.ApiKeyService,
        "resolve_api_key_principal",
        fake_resolve_api_key_principal,
    )
    monkeypatch.setattr(api_key_service_module.ApiKeyService, "enforce_limits", fake_enforce_limits)
    monkeypatch.setattr(api_key_service_module.ApiKeyService, "log_usage", fake_log_usage)
    monkeypatch.setattr(
        template_service_module.TemplateService,
        "list_templates",
        fake_list_templates,
    )

    response = client.get(
        "/api/v1/public/templates",
        headers={
            "X-API-Key": "public-test-key",
            "X-Request-ID": "req-public-1",
            "X-Correlation-ID": "corr-public-1",
        },
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["organization_id"] == str(principal.organization_id)
    assert usage_log["api_key_id"] == principal.api_key_id
    assert usage_log["method"] == "GET"
    assert str(usage_log["path"]).endswith("/public/templates")
    assert usage_log["status_code"] == 200
    assert usage_log["rate_limited"] is False
    assert usage_log["request_id"] == "req-public-1"
    assert usage_log["correlation_id"] == "corr-public-1"


def test_public_document_generation_uses_api_key_org_and_scope(
    monkeypatch,
    client: TestClient,
) -> None:
    """Generation requests should use the API key organization and machine identity."""
    principal = build_principal(
        scopes=(ApiKeyScope.DOCUMENTS_GENERATE,),
        required_scope=ApiKeyScope.DOCUMENTS_GENERATE,
    )
    task_id = uuid4()
    template_id = uuid4()

    async def fake_resolve_api_key_principal(self, *, raw_key, required_scope):
        assert raw_key == "generate-key"
        return build_principal(
            scopes=(ApiKeyScope.DOCUMENTS_GENERATE,),
            required_scope=required_scope,
            organization_id=principal.organization_id,
            api_key_id=principal.api_key_id,
        )

    async def fake_enforce_limits(self, api_principal):
        _ = api_principal
        return None

    async def fake_log_usage(self, **kwargs):
        _ = kwargs
        return None

    async def fake_create_job(
        self,
        payload: DocumentJobCreateRequest,
        background_tasks: BackgroundTasks,
        *,
        current_user_id,
        current_api_key_id=None,
        require_published_template=False,
    ) -> DocumentJobResponse:
        assert payload.organization_id == principal.organization_id
        assert payload.template_id == template_id
        assert background_tasks is not None
        assert current_user_id is None
        assert current_api_key_id == principal.api_key_id
        assert require_published_template is True
        return DocumentJobResponse(
            task_id=task_id,
            organization_id=payload.organization_id,
            status="queued",
            template_id=payload.template_id,
            template_version_id=payload.template_version_id,
            requested_by_user_id=None,
            from_cache=False,
        )

    monkeypatch.setattr(
        api_key_service_module.ApiKeyService,
        "resolve_api_key_principal",
        fake_resolve_api_key_principal,
    )
    monkeypatch.setattr(api_key_service_module.ApiKeyService, "enforce_limits", fake_enforce_limits)
    monkeypatch.setattr(api_key_service_module.ApiKeyService, "log_usage", fake_log_usage)
    monkeypatch.setattr(document_service_module.DocumentService, "create_job", fake_create_job)

    response = client.post(
        "/api/v1/public/documents/generate",
        headers={"X-API-Key": "generate-key"},
        json={
            "template_id": str(template_id),
            "data": {"student_name": "Anek"},
            "constructor": {
                "blocks": [
                    {
                        "type": "text",
                        "id": "text-1",
                        "binding": {"key": "student_name"},
                    }
                ]
            },
        },
    )

    assert response.status_code == 202
    assert response.json()["organization_id"] == str(principal.organization_id)
    assert response.json()["requested_by_user_id"] is None


def test_public_scope_denial_is_logged(monkeypatch, client: TestClient) -> None:
    """Requests with a valid key but missing scope should return 403 and still be logged."""
    usage_log: dict[str, object] = {}

    async def fake_resolve_api_key_principal(self, *, raw_key, required_scope):
        _ = raw_key
        return build_principal(
            scopes=(ApiKeyScope.TEMPLATES_READ,),
            required_scope=required_scope,
        )

    async def fake_log_usage(
        self,
        *,
        principal,
        method,
        path,
        status_code,
        rate_limited,
        request_id=None,
        correlation_id=None,
    ):
        _ = method, path
        usage_log.update(
            {
                "scope": principal.scope,
                "status_code": status_code,
                "rate_limited": rate_limited,
                "request_id": request_id,
                "correlation_id": correlation_id,
            }
        )

    monkeypatch.setattr(
        api_key_service_module.ApiKeyService,
        "resolve_api_key_principal",
        fake_resolve_api_key_principal,
    )
    monkeypatch.setattr(api_key_service_module.ApiKeyService, "log_usage", fake_log_usage)

    response = client.get(
        "/api/v1/public/documents/constructor-schema",
        headers={
            "X-API-Key": "limited-key",
            "X-Request-ID": "req-public-403",
            "X-Correlation-ID": "corr-public-403",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "API key does not grant the requested scope."
    assert usage_log["scope"] == ApiKeyScope.DOCUMENTS_GENERATE
    assert usage_log["status_code"] == 403
    assert usage_log["rate_limited"] is False
    assert usage_log["request_id"] == "req-public-403"
    assert usage_log["correlation_id"] == "corr-public-403"


def test_public_rate_limit_response_is_logged(monkeypatch, client: TestClient) -> None:
    """Rate-limited public requests should return 429 and persist usage metadata."""
    principal = build_principal(
        scopes=(ApiKeyScope.DOCUMENTS_READ,),
        required_scope=ApiKeyScope.DOCUMENTS_READ,
    )
    usage_log: dict[str, object] = {}

    async def fake_resolve_api_key_principal(self, *, raw_key, required_scope):
        _ = raw_key
        return build_principal(
            scopes=(ApiKeyScope.DOCUMENTS_READ,),
            required_scope=required_scope,
            organization_id=principal.organization_id,
            api_key_id=principal.api_key_id,
        )

    async def fake_enforce_limits(self, api_principal):
        _ = api_principal
        raise TooManyRequestsError("API key rate limit exceeded.")

    async def fake_log_usage(
        self,
        *,
        principal,
        method,
        path,
        status_code,
        rate_limited,
        request_id=None,
        correlation_id=None,
    ):
        _ = method, request_id, correlation_id
        usage_log.update(
            {
                "api_key_id": principal.api_key_id,
                "status_code": status_code,
                "rate_limited": rate_limited,
                "path": path,
            }
        )

    monkeypatch.setattr(
        api_key_service_module.ApiKeyService,
        "resolve_api_key_principal",
        fake_resolve_api_key_principal,
    )
    monkeypatch.setattr(api_key_service_module.ApiKeyService, "enforce_limits", fake_enforce_limits)
    monkeypatch.setattr(api_key_service_module.ApiKeyService, "log_usage", fake_log_usage)

    response = client.get(
        f"/api/v1/public/documents/jobs/{uuid4()}",
        headers={"X-API-Key": "rate-limited-key"},
    )

    assert response.status_code == 429
    assert response.json()["detail"] == "API key rate limit exceeded."
    assert usage_log["api_key_id"] == principal.api_key_id
    assert usage_log["status_code"] == 429
    assert usage_log["rate_limited"] is True
    assert str(usage_log["path"]).endswith("/public/documents/jobs/{task_id}")


def test_public_audit_route_uses_audit_scope_and_org(monkeypatch, client: TestClient) -> None:
    """Audit reads should be available on the public API only with the audit scope."""
    issued_at = datetime(2026, 2, 1, 12, 0, tzinfo=timezone.utc)
    principal = build_principal(
        scopes=(ApiKeyScope.AUDIT_READ,),
        required_scope=ApiKeyScope.AUDIT_READ,
    )

    async def fake_resolve_api_key_principal(self, *, raw_key, required_scope):
        assert raw_key == "audit-key"
        assert required_scope == ApiKeyScope.AUDIT_READ
        return build_principal(
            scopes=(ApiKeyScope.AUDIT_READ,),
            required_scope=required_scope,
            organization_id=principal.organization_id,
            api_key_id=principal.api_key_id,
        )

    async def fake_enforce_limits(self, api_principal):
        _ = api_principal
        return None

    async def fake_log_usage(self, **kwargs):
        _ = kwargs
        return None

    async def fake_list_recent_audit_events(self, *, organization_id, limit):
        assert organization_id == principal.organization_id
        assert limit == 25
        return AuditEventListResponse(
            items=[
                AuditEventDiagnosticResponse(
                    id=uuid4(),
                    organization_id=organization_id,
                    user_id=None,
                    action="document_job_created",
                    entity_type="document_job",
                    entity_id=uuid4(),
                    payload={},
                    created_at=issued_at,
                )
            ]
        )

    monkeypatch.setattr(
        api_key_service_module.ApiKeyService,
        "resolve_api_key_principal",
        fake_resolve_api_key_principal,
    )
    monkeypatch.setattr(api_key_service_module.ApiKeyService, "enforce_limits", fake_enforce_limits)
    monkeypatch.setattr(api_key_service_module.ApiKeyService, "log_usage", fake_log_usage)
    monkeypatch.setattr(
        operations_service_module.OperationsService,
        "list_recent_audit_events",
        fake_list_recent_audit_events,
    )

    response = client.get(
        "/api/v1/public/audit/events",
        headers={"X-API-Key": "audit-key"},
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["organization_id"] == str(principal.organization_id)


def test_public_document_read_routes_use_api_key_org(monkeypatch, client: TestClient) -> None:
    """Document polling routes should stay tenant-scoped to the API key."""
    principal = build_principal(
        scopes=(ApiKeyScope.DOCUMENTS_READ,),
        required_scope=ApiKeyScope.DOCUMENTS_READ,
    )
    task_id = uuid4()

    async def fake_resolve_api_key_principal(self, *, raw_key, required_scope):
        assert raw_key == "read-key"
        return build_principal(
            scopes=(ApiKeyScope.DOCUMENTS_READ,),
            required_scope=required_scope,
            organization_id=principal.organization_id,
            api_key_id=principal.api_key_id,
        )

    async def fake_enforce_limits(self, api_principal):
        _ = api_principal
        return None

    async def fake_log_usage(self, **kwargs):
        _ = kwargs
        return None

    async def fake_get_job_status(self, *, organization_id, job_id) -> DocumentJobStatusResponse:
        assert organization_id == principal.organization_id
        assert job_id == task_id
        return DocumentJobStatusResponse(
            task_id=job_id,
            organization_id=organization_id,
            status="completed",
            template_id=uuid4(),
            template_version_id=uuid4(),
            requested_by_user_id=None,
            from_cache=False,
            error_message=None,
            created_at=datetime(2026, 2, 2, 9, 0, tzinfo=timezone.utc),
            started_at=datetime(2026, 2, 2, 9, 0, 1, tzinfo=timezone.utc),
            completed_at=datetime(2026, 2, 2, 9, 0, 2, tzinfo=timezone.utc),
            artifacts=[],
        )

    monkeypatch.setattr(
        api_key_service_module.ApiKeyService,
        "resolve_api_key_principal",
        fake_resolve_api_key_principal,
    )
    monkeypatch.setattr(api_key_service_module.ApiKeyService, "enforce_limits", fake_enforce_limits)
    monkeypatch.setattr(api_key_service_module.ApiKeyService, "log_usage", fake_log_usage)
    monkeypatch.setattr(
        document_service_module.DocumentService,
        "get_job_status",
        fake_get_job_status,
    )

    response = client.get(
        f"/api/v1/public/documents/jobs/{task_id}",
        headers={"X-API-Key": "read-key"},
    )

    assert response.status_code == 200
    assert response.json()["organization_id"] == str(principal.organization_id)


def test_public_verify_route_returns_matching_artifact(monkeypatch, client: TestClient) -> None:
    """Public verification should stay scoped to the API key's organization."""
    principal = build_principal(
        scopes=(ApiKeyScope.DOCUMENTS_READ,),
        required_scope=ApiKeyScope.DOCUMENTS_READ,
    )
    artifact_id = uuid4()
    task_id = uuid4()
    authenticity_hash = "b" * 64

    async def fake_resolve_api_key_principal(self, *, raw_key, required_scope):
        assert raw_key == "read-key"
        return build_principal(
            scopes=(ApiKeyScope.DOCUMENTS_READ,),
            required_scope=required_scope,
            organization_id=principal.organization_id,
            api_key_id=principal.api_key_id,
        )

    async def fake_enforce_limits(self, api_principal):
        _ = api_principal
        return None

    async def fake_log_usage(self, **kwargs):
        _ = kwargs
        return None

    async def fake_verify_artifact(
        self,
        *,
        organization_id,
        authenticity_hash=None,
        file_bytes=None,
    ) -> DocumentVerificationResponse:
        assert organization_id == principal.organization_id
        assert authenticity_hash == "b" * 64
        assert file_bytes is None
        return DocumentVerificationResponse(
            organization_id=organization_id,
            matched=True,
            provided_hash=authenticity_hash,
            matched_artifact_count=1,
            artifact=DocumentVerificationArtifactResponse(
                artifact_id=artifact_id,
                task_id=task_id,
                kind="pdf",
                file_name="certificate-1.0.0.pdf",
                content_type="application/pdf",
                size_bytes=1024,
                issued_at=datetime(2026, 2, 21, 9, 30, tzinfo=timezone.utc),
                authenticity_hash=authenticity_hash,
                verification_code="VER-ABCDEF12-BBBBBBBBBBBB",
            ),
        )

    monkeypatch.setattr(
        api_key_service_module.ApiKeyService,
        "resolve_api_key_principal",
        fake_resolve_api_key_principal,
    )
    monkeypatch.setattr(api_key_service_module.ApiKeyService, "enforce_limits", fake_enforce_limits)
    monkeypatch.setattr(api_key_service_module.ApiKeyService, "log_usage", fake_log_usage)
    monkeypatch.setattr(document_service_module.DocumentService, "verify_artifact", fake_verify_artifact)

    response = client.post(
        "/api/v1/public/documents/verify",
        headers={"X-API-Key": "read-key"},
        data={"authenticity_hash": authenticity_hash},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["organization_id"] == str(principal.organization_id)
    assert payload["artifact"]["artifact_id"] == str(artifact_id)
