"""API contract tests for shipped frontend-facing wire formats."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import BackgroundTasks
from fastapi.testclient import TestClient

from app.dtos.document import (
    DocumentArtifactResponse,
    DocumentJobCreateRequest,
    DocumentJobResponse,
    DocumentJobStatusResponse,
)
from app.services.document_service import DocumentService
from tests.conftest import build_docx_fixture

pytestmark = pytest.mark.integration


def test_extract_schema_contract_matches_current_api_contract(
    authenticated_client: TestClient,
) -> None:
    """Lock the schema extraction response payload."""
    response = authenticated_client.post(
        "/api/v1/templates/extract-schema",
        files={
            "file": (
                "certificate.docx",
                build_docx_fixture("{{student_name}}", "{{table_scores}}"),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "variable_count": 2,
        "variables": [
            {
                "key": "student_name",
                "label": "Student Name",
                "placeholder": "{{student_name}}",
                "value_type": "string",
                "component_type": "text",
                "required": True,
                "sample_value": None,
                "occurrences": 1,
                "sources": ["word/document.xml"],
            },
            {
                "key": "table_scores",
                "label": "Table Scores",
                "placeholder": "{{table_scores}}",
                "value_type": "array",
                "component_type": "table",
                "required": True,
                "sample_value": None,
                "occurrences": 1,
                "sources": ["word/document.xml"],
            },
        ],
        "components": [
            {
                "id": "student_name",
                "component": "text",
                "binding": "student_name",
                "label": "Student Name",
                "value_type": "string",
                "required": True,
            },
            {
                "id": "table_scores",
                "component": "table",
                "binding": "table_scores",
                "label": "Table Scores",
                "value_type": "array",
                "required": True,
            },
        ],
    }


@pytest.mark.parametrize(
    "route",
    [
        "/api/v1/documents/generate",
        "/api/v1/documents/jobs",
    ],
)
def test_document_job_creation_contract_matches_current_api_contract(
    authenticated_client: TestClient,
    authenticated_membership,
    monkeypatch,
    route: str,
) -> None:
    """Lock the queued-job response shared by both generation endpoints."""
    organization_id = authenticated_membership.organization_id
    template_id = uuid4()
    template_version_id = uuid4()
    task_id = uuid4()

    async def fake_create_job(
        self: DocumentService,
        payload: DocumentJobCreateRequest,
        background_tasks: BackgroundTasks,
        *,
        current_user_id,
    ) -> DocumentJobResponse:
        """Return the shipped queued-job response shape."""
        assert payload.organization_id == organization_id
        assert payload.template_id == template_id
        assert payload.template_version_id == template_version_id
        assert current_user_id == authenticated_membership.user_id
        assert payload.data == {"student_name": "Anek"}
        assert background_tasks is not None
        return DocumentJobResponse(
            task_id=task_id,
            organization_id=payload.organization_id,
            status="queued",
            template_id=payload.template_id,
            template_version_id=payload.template_version_id,
            requested_by_user_id=current_user_id,
            from_cache=False,
        )

    monkeypatch.setattr(DocumentService, "create_job", fake_create_job)

    response = authenticated_client.post(
        route,
        json={
            "organization_id": str(organization_id),
            "template_id": str(template_id),
            "template_version_id": str(template_version_id),
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
    assert response.json() == {
        "task_id": str(task_id),
        "organization_id": str(organization_id),
        "status": "queued",
        "template_id": str(template_id),
        "template_version_id": str(template_version_id),
        "requested_by_user_id": str(authenticated_membership.user_id),
        "from_cache": False,
    }


def test_constructor_schema_contract_matches_current_api_contract(
    authenticated_client: TestClient,
) -> None:
    """Lock the shipped constructor schema discovery payload."""
    response = authenticated_client.get("/api/v1/documents/constructor-schema")

    assert response.status_code == 200
    assert response.json() == {
        "descriptor": {
            "schema_version": "1.0",
            "default_formatting": {
                "page": {
                    "profile": "gost_r_7_0_97_2016",
                    "paper_size": "A4",
                    "orientation": "portrait",
                    "margin_left_mm": 30.0,
                    "margin_right_mm": 10.0,
                    "margin_top_mm": 20.0,
                    "margin_bottom_mm": 20.0,
                    "header_distance_mm": 12.5,
                    "footer_distance_mm": 12.5,
                },
                "typography": {
                    "font_family": "Times New Roman",
                    "font_size_pt": 14.0,
                    "line_spacing": 1.5,
                    "first_line_indent_mm": 12.5,
                    "paragraph_spacing_before_pt": 0.0,
                    "paragraph_spacing_after_pt": 0.0,
                    "alignment": "justify",
                },
                "allow_orphan_headings": False,
                "repeat_table_header_on_each_page": True,
                "force_table_borders": True,
                "signatures_align_right": True,
            },
            "supported_blocks": [
                "text",
                "table",
                "image",
                "header",
                "signature",
                "page_break",
                "spacer",
            ],
        }
    }


def test_document_job_polling_contract_matches_current_api_contract(
    authenticated_client: TestClient,
    authenticated_membership,
    monkeypatch,
) -> None:
    """Lock the polling payload returned for completed document jobs."""
    organization_id = authenticated_membership.organization_id
    template_id = uuid4()
    template_version_id = uuid4()
    requested_by_user_id = uuid4()
    task_id = uuid4()
    artifact_id = uuid4()

    async def fake_get_job_status(
        self: DocumentService,
        *,
        organization_id,
        job_id,
    ) -> DocumentJobStatusResponse:
        """Return the shipped polling response shape."""
        assert organization_id == expected_organization_id
        assert job_id == task_id
        return DocumentJobStatusResponse(
            task_id=task_id,
            organization_id=organization_id,
            status="completed",
            template_id=template_id,
            template_version_id=template_version_id,
            requested_by_user_id=requested_by_user_id,
            from_cache=False,
            error_message=None,
            created_at=datetime(2025, 1, 10, 10, 0, 0, tzinfo=timezone.utc),
            started_at=datetime(2025, 1, 10, 10, 0, 1, tzinfo=timezone.utc),
            completed_at=datetime(2025, 1, 10, 10, 0, 3, tzinfo=timezone.utc),
            artifacts=[
                DocumentArtifactResponse(
                    id=artifact_id,
                    kind="pdf",
                    file_name="certificate-1.0.0.pdf",
                    content_type="application/pdf",
                    size_bytes=12034,
                    download_url="https://storage.test/artifacts/certificate-1.0.0.pdf",
                )
            ],
        )

    expected_organization_id = organization_id
    monkeypatch.setattr(DocumentService, "get_job_status", fake_get_job_status)

    response = authenticated_client.get(
        f"/api/v1/documents/jobs/{task_id}",
        params={"organization_id": str(organization_id)},
    )

    assert response.status_code == 200
    assert response.json() == {
        "task_id": str(task_id),
        "organization_id": str(organization_id),
        "status": "completed",
        "template_id": str(template_id),
        "template_version_id": str(template_version_id),
        "requested_by_user_id": str(requested_by_user_id),
        "from_cache": False,
        "error_message": None,
        "created_at": "2025-01-10T10:00:00Z",
        "started_at": "2025-01-10T10:00:01Z",
        "completed_at": "2025-01-10T10:00:03Z",
        "artifacts": [
            {
                "id": str(artifact_id),
                "kind": "pdf",
                "file_name": "certificate-1.0.0.pdf",
                "content_type": "application/pdf",
                "size_bytes": 12034,
                "download_url": "https://storage.test/artifacts/certificate-1.0.0.pdf",
            }
        ],
    }
