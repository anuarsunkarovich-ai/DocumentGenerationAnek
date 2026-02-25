"""Integration tests for document-related API routes."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import BackgroundTasks
from fastapi.testclient import TestClient

from app.dtos.document import (
    DocumentJobCreateRequest,
    DocumentJobResponse,
    DocumentVerificationArtifactResponse,
    DocumentVerificationResponse,
)
from app.services.document_service import DocumentService

pytestmark = pytest.mark.integration


def test_generate_endpoint_returns_task_id(
    authenticated_client: TestClient,
    authenticated_membership,
    monkeypatch,
) -> None:
    """Ensure the generate route accepts a valid payload and returns a task id."""
    organization_id = authenticated_membership.organization_id
    template_id = uuid4()
    task_id = uuid4()

    async def fake_create_job(
        self: DocumentService,
        payload: DocumentJobCreateRequest,
        background_tasks: BackgroundTasks,
        *,
        current_user_id,
        current_api_key_id=None,
        require_published_template: bool = False,
    ) -> DocumentJobResponse:
        """Return a predictable queued job for the route integration test."""
        assert payload.organization_id == organization_id
        assert payload.template_id == template_id
        assert payload.data["student_name"] == "Anek"
        assert current_user_id == authenticated_membership.user_id
        assert current_api_key_id is None
        assert require_published_template is False
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
        "/api/v1/documents/generate",
        json={
            "organization_id": str(organization_id),
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
    payload = response.json()

    assert payload["task_id"] == str(task_id)
    assert payload["organization_id"] == str(organization_id)
    assert payload["status"] == "queued"


def test_verify_endpoint_returns_matching_artifact(
    authenticated_client: TestClient,
    authenticated_membership,
    monkeypatch,
) -> None:
    """Ensure the verification route accepts an authenticity hash and returns match metadata."""
    organization_id = authenticated_membership.organization_id
    artifact_id = uuid4()
    task_id = uuid4()
    authenticity_hash = "a" * 64

    async def fake_verify_artifact(
        self: DocumentService,
        *,
        organization_id,
        authenticity_hash=None,
        file_bytes=None,
    ) -> DocumentVerificationResponse:
        assert organization_id == authenticated_membership.organization_id
        assert authenticity_hash == "a" * 64
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
                size_bytes=2048,
                issued_at=datetime(2026, 2, 21, 9, 30, tzinfo=timezone.utc),
                authenticity_hash=authenticity_hash,
                verification_code="VER-ABCDEF12-AAAAAAAAAAAA",
            ),
        )

    monkeypatch.setattr(DocumentService, "verify_artifact", fake_verify_artifact)

    response = authenticated_client.post(
        "/api/v1/documents/verify",
        data={
            "organization_id": str(organization_id),
            "authenticity_hash": authenticity_hash,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["matched"] is True
    assert payload["provided_hash"] == authenticity_hash
    assert payload["artifact"]["artifact_id"] == str(artifact_id)
