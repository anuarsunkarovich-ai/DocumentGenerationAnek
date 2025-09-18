"""Integration tests for document-related API routes."""

from uuid import uuid4

import pytest
from fastapi import BackgroundTasks
from fastapi.testclient import TestClient

from app.dtos.document import DocumentJobCreateRequest, DocumentJobResponse
from app.services.document_service import DocumentService

pytestmark = pytest.mark.integration


def test_generate_endpoint_returns_task_id(
    client: TestClient,
    monkeypatch,
) -> None:
    """Ensure the generate route accepts a valid payload and returns a task id."""
    organization_id = uuid4()
    template_id = uuid4()
    task_id = uuid4()

    async def fake_create_job(
        self: DocumentService,
        payload: DocumentJobCreateRequest,
        background_tasks: BackgroundTasks,
    ) -> DocumentJobResponse:
        """Return a predictable queued job for the route integration test."""
        assert payload.organization_id == organization_id
        assert payload.template_id == template_id
        assert payload.data["student_name"] == "Anek"
        assert background_tasks is not None
        return DocumentJobResponse(
            task_id=task_id,
            organization_id=payload.organization_id,
            status="queued",
            template_id=payload.template_id,
            template_version_id=payload.template_version_id,
            requested_by_user_id=payload.requested_by_user_id,
            from_cache=False,
        )

    monkeypatch.setattr(DocumentService, "create_job", fake_create_job)

    response = client.post(
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
