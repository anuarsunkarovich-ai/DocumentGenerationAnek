"""Integration tests for role-based authorization and tenant enforcement."""

from types import SimpleNamespace
from typing import Generator
from uuid import uuid4

import pytest
from fastapi import BackgroundTasks
from fastapi.testclient import TestClient

from app.api.dependencies.auth import CurrentMembership, get_current_membership, get_current_user
from app.core.exceptions import AuthorizationError
from app.dtos.document import DocumentJobCreateRequest, DocumentJobResponse
from app.dtos.template import (
    TemplateIngestionResponse,
    TemplateResponse,
    TemplateSchemaResponse,
    TemplateVersionResponse,
)
from app.main import app
from app.models.enums import UserRole
from app.services.document_service import DocumentService
from app.services.template_service import TemplateService
from tests.conftest import build_docx_fixture, create_test_client

pytestmark = pytest.mark.integration


def build_current_user(*, role: UserRole, organization_id=None, extra_memberships=None):
    """Build a fake authenticated user with memberships for route authorization tests."""
    organization_id = organization_id or uuid4()
    organization = SimpleNamespace(
        id=organization_id,
        name="Math Department",
        code="math-dept",
        is_active=True,
    )
    memberships = [
        SimpleNamespace(
            id=uuid4(),
            organization_id=organization_id,
            role=role,
            is_active=True,
            is_default=True,
            organization=organization,
        )
    ]
    if extra_memberships:
        memberships.extend(extra_memberships)
    return SimpleNamespace(
        id=uuid4(),
        organization_id=organization_id,
        email="anek@example.com",
        full_name="Anek",
        role=role,
        is_active=True,
        organization=organization,
        memberships=memberships,
    )


def build_client_for_user(user) -> Generator[TestClient, None, None]:
    """Override auth dependencies with one fake current user."""
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_membership] = lambda: CurrentMembership(
        user=user,
        membership=user.memberships[0],
    )
    try:
        yield create_test_client()
    finally:
        app.dependency_overrides.clear()


def test_viewer_can_read_templates(monkeypatch) -> None:
    """Ensure viewers retain read access to template listings."""
    user = build_current_user(role=UserRole.VIEWER)

    async def fake_list_templates(
        self: TemplateService,
        organization_id,
        *,
        published_only: bool = False,
    ):
        assert published_only is False
        return {"items": []}

    monkeypatch.setattr(TemplateService, "list_templates", fake_list_templates)

    for client in build_client_for_user(user):
        response = client.get("/api/v1/templates", params={"organization_id": str(user.organization_id)})

    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_operator_can_generate_documents(monkeypatch) -> None:
    """Ensure operators can create generation jobs."""
    user = build_current_user(role=UserRole.OPERATOR)
    task_id = uuid4()
    template_id = uuid4()

    async def fake_create_job(
        self: DocumentService,
        payload: DocumentJobCreateRequest,
        background_tasks: BackgroundTasks,
        *,
        current_user_id,
        current_api_key_id=None,
        require_published_template: bool = False,
    ) -> DocumentJobResponse:
        assert payload.organization_id == user.organization_id
        assert current_user_id == user.id
        assert current_api_key_id is None
        assert require_published_template is False
        assert background_tasks is not None
        return DocumentJobResponse(
            task_id=task_id,
            organization_id=payload.organization_id,
            status="queued",
            template_id=template_id,
            template_version_id=payload.template_version_id,
            requested_by_user_id=current_user_id,
            from_cache=False,
        )

    monkeypatch.setattr(DocumentService, "create_job", fake_create_job)

    for client in build_client_for_user(user):
        response = client.post(
            "/api/v1/documents/generate",
            json={
                "organization_id": str(user.organization_id),
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
    assert response.json()["requested_by_user_id"] == str(user.id)


def test_viewer_cannot_generate_documents(monkeypatch) -> None:
    """Ensure viewers cannot create generation jobs."""
    user = build_current_user(role=UserRole.VIEWER)
    monkeypatch.setattr(DocumentService, "create_job", lambda *args, **kwargs: None)

    for client in build_client_for_user(user):
        response = client.post(
            "/api/v1/documents/generate",
            json={
                "organization_id": str(user.organization_id),
                "template_id": str(uuid4()),
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

    assert response.status_code == 403
    assert response.json()["detail"] == "User does not have permission to generate documents."


def test_manager_can_upload_templates(monkeypatch) -> None:
    """Ensure managers retain template write access."""
    user = build_current_user(role=UserRole.MANAGER)
    version_id = uuid4()

    async def fake_upload_template(self: TemplateService, **kwargs) -> TemplateIngestionResponse:
        assert kwargs["organization_id"] == user.organization_id
        assert kwargs["current_user_id"] == user.id
        return TemplateIngestionResponse(
            template=TemplateResponse(
                id=uuid4(),
                organization_id=user.organization_id,
                name="Certificate",
                code="certificate",
                status="active",
                description=None,
                current_version=None,
            ),
            version=TemplateVersionResponse(
                id=version_id,
                version="1.0.0",
                is_current=True,
                is_published=True,
                original_filename="certificate.docx",
                storage_key="templates/math-dept/certificate/1.0.0/certificate.docx",
                checksum=None,
                notes=None,
                schema_payload=TemplateSchemaResponse(
                    variable_count=0,
                    variables=[],
                    components=[],
                ),
            ),
        )

    monkeypatch.setattr(TemplateService, "upload_template", fake_upload_template)

    for client in build_client_for_user(user):
        response = client.post(
            "/api/v1/templates/upload",
            data={
                "organization_id": str(user.organization_id),
                "name": "Certificate",
                "code": "certificate",
                "version": "1.0.0",
                "publish": "true",
            },
            files={
                "file": (
                    "certificate.docx",
                    build_docx_fixture("{{student_name}}"),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )

    assert response.status_code == 201
    assert response.json()["version"]["id"] == str(version_id)


def test_viewer_cannot_upload_templates(monkeypatch) -> None:
    """Ensure viewers are denied template write access."""
    user = build_current_user(role=UserRole.VIEWER)
    monkeypatch.setattr(TemplateService, "upload_template", lambda *args, **kwargs: None)

    for client in build_client_for_user(user):
        response = client.post(
            "/api/v1/templates/upload",
            data={
                "organization_id": str(user.organization_id),
                "name": "Certificate",
                "code": "certificate",
                "version": "1.0.0",
            },
            files={
                "file": (
                    "certificate.docx",
                    build_docx_fixture("{{student_name}}"),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "User does not have permission to modify templates."


def test_wrong_org_request_is_rejected(monkeypatch) -> None:
    """Ensure same-user requests cannot target a foreign organization id."""
    user = build_current_user(role=UserRole.ADMIN)
    foreign_organization_id = uuid4()
    monkeypatch.setattr(TemplateService, "list_templates", lambda *args, **kwargs: None)

    for client in build_client_for_user(user):
        response = client.get(
            "/api/v1/templates",
            params={"organization_id": str(foreign_organization_id)},
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "User does not have access to this organization."


def test_cross_tenant_membership_validation_rejects_unowned_org(monkeypatch) -> None:
    """Ensure users with one membership cannot hop into another tenant."""
    first_org_id = uuid4()
    second_org_id = uuid4()
    third_org_id = uuid4()
    extra_membership = SimpleNamespace(
        id=uuid4(),
        organization_id=second_org_id,
        role=UserRole.OPERATOR,
        is_active=True,
        is_default=False,
        organization=SimpleNamespace(
            id=second_org_id,
            name="Second Org",
            code="second-org",
            is_active=True,
        ),
    )
    user = build_current_user(
        role=UserRole.OPERATOR,
        organization_id=first_org_id,
        extra_memberships=[extra_membership],
    )
    monkeypatch.setattr(DocumentService, "get_job_status", lambda *args, **kwargs: None)

    for client in build_client_for_user(user):
        response = client.get(
            f"/api/v1/documents/jobs/{uuid4()}",
            params={"organization_id": str(third_org_id)},
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "User does not have access to this organization."


def test_admin_only_audit_access_helper() -> None:
    """Ensure audit access stays restricted to admins."""
    from app.api.dependencies.authorization import require_audit_access

    admin_user = build_current_user(role=UserRole.ADMIN)
    manager_user = build_current_user(role=UserRole.MANAGER)

    membership = require_audit_access(admin_user, admin_user.organization_id)

    assert membership.role == UserRole.ADMIN

    with pytest.raises(AuthorizationError):
        require_audit_access(manager_user, manager_user.organization_id)
